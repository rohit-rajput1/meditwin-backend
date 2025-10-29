from .dependency import openai_client, pinecone_index
from .utils import generate_namespace, ocr_image, create_file_id
from pypdf import PdfReader
from fastapi import UploadFile
from database.models.report import Report
from database.settings import AsyncSessionLocal
from sqlalchemy import update
from datetime import datetime, timezone
import io

async def extract_text(file: UploadFile, content: bytes = None) -> str:
    filename = file.filename.lower()

    if content is None:
        content = await file.read()
        await file.seek(0)

    if filename.endswith(".pdf"):
        try:
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            # If PDF has no text, try OCR on it
            if not text.strip():
                print(f"PDF has no extractable text, attempting OCR...")
                text = await ocr_image(content)
            
            return text.strip()
        except Exception as e:
            print(f"PDF extraction failed: {e}")
            return ""
    elif filename.endswith(("jpg", "jpeg", "png")):
        try:
            text = await ocr_image(content)
            print(f"OCR extracted {len(text)} characters from image")
            return text
        except Exception as e:
            print(f"Image OCR failed: {e}")
            return ""
    else:
        return ""

async def generate_embedding(text: str):
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000]
        )
        embedding = response.data[0].embedding
        if len(embedding) != 1536:
            raise RuntimeError(f"Wrong embedding dimension! Got {len(embedding)}")
        return embedding
    except Exception as e:
        raise RuntimeError(f"OpenAI embedding failed: {e}")

async def upload_to_pinecone(file_id, filename, embedding):
    """
    Upsert embedding to Pinecone. Only store vectors here; not in Postgres.
    """
    try:
        namespace = generate_namespace(file_id, filename)
        response = pinecone_index.upsert(
            vectors=[(str(file_id), embedding, {"filename": filename})],
            namespace=namespace
        )
        if response.upserted_count == 0:
            print(f"Warning: No vectors were upserted for namespace {namespace}")
        else:
            print(f"Upserted {response.upserted_count} vector(s) into namespace: {namespace}")
        return namespace
    except Exception as e:
        raise RuntimeError(f"Pinecone upsert failed: {e}")

async def process_upload(file: UploadFile, file_id=None, content: bytes = None):
    try:
        if file_id is None:
            file_id = create_file_id()

        print(f"Processing file: {file.filename} with ID: {file_id}")

        # Extract text
        text = await extract_text(file, content)
        if not text.strip():
            raise RuntimeError("No text extracted from file")

        # Generate embedding
        embedding = await generate_embedding(text)

        # Upload embedding to Pinecone
        namespace = await upload_to_pinecone(file_id, file.filename, embedding)

        # Update Postgres report metadata (summary, insights, status)
        async with AsyncSessionLocal() as session:
            stmt = (
                update(Report)
                .where(Report.report_id == file_id)
                .values(
                    summary={"text_length": len(text)},
                    insights={"namespace": namespace},
                    status="completed",
                    uploaded_at=datetime.now(timezone.utc)
                )
            )
            await session.execute(stmt)
            await session.commit()

        print(f"File {file.filename} processed successfully.")
        return file_id

    except Exception as e:
        print(f"Error in process_upload: {e}")
        # Update Postgres status to failed
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(Report)
                .where(Report.report_id == file_id)
                .values(status="failed", insights={"error": str(e)})
            )
            await session.commit()
        raise
