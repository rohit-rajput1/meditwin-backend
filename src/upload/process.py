import io
from datetime import datetime, timezone
from fastapi import UploadFile
from sqlalchemy import update
from pypdf import PdfReader
from pdf2image import convert_from_bytes
from PIL import Image
from database.models.report import Report
from database.settings import AsyncSessionLocal
from .dependency import openai_client, pinecone_index
from .utils import generate_namespace, ocr_image, create_file_id

MIN_TEXT_LENGTH = 20

async def extract_text_from_pdf_with_vision(content: bytes) -> str:
    """Extract text from PDF using OpenAI Vision API for scanned PDFs."""
    try:
        images = convert_from_bytes(content, dpi=300)
        all_text = []
        
        for i, img in enumerate(images):
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            
            try:
                page_text = await ocr_image(img_bytes.getvalue(), is_medical_document=True)
                if page_text:
                    all_text.append(f"--- Page {i+1} ---\n{page_text}")
            except Exception:
                continue
        
        return "\n\n".join(all_text)
        
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {str(e)}")

async def extract_text(file: UploadFile, content: bytes = None, is_medical: bool = True) -> str:
    """Extract text from PDF or image using OpenAI Vision for OCR."""
    try:
        filename = file.filename.lower()
        if content is None:
            content = await file.read()
            await file.seek(0)
        
        # PDF Handling
        if filename.endswith(".pdf"):
            try:
                pdf_file = io.BytesIO(content)
                reader = PdfReader(pdf_file)
                text = ""
                
                # Try standard text extraction first
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                # If insufficient text, use Vision API
                if len(text.strip()) < MIN_TEXT_LENGTH:
                    text = await extract_text_from_pdf_with_vision(content)
                
                return text.strip()
                
            except Exception as e:
                raise RuntimeError(f"PDF processing error: {str(e)}")
        
        # Image Handling
        elif filename.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif")):
            try:
                text = await ocr_image(content, is_medical_document=is_medical)
                return text
            except Exception as e:
                raise RuntimeError(f"Image OCR error: {str(e)}")
        
        # Unsupported file
        else:
            raise RuntimeError(f"Unsupported file type: {filename}")
            
    except Exception as e:
        raise RuntimeError(f"Text extraction failed: {str(e)}")

async def generate_embedding(text: str):
    """Generate OpenAI embedding for the given text."""
    try:
        text_length = len(text.strip())
        
        if text_length < MIN_TEXT_LENGTH:
            raise RuntimeError(
                f"Text too short for embedding: {text_length} characters "
                f"(minimum {MIN_TEXT_LENGTH} required)"
            )
        
        truncated_text = text[:8000]
        
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=truncated_text
        )
        embedding = response.data[0].embedding
        
        if len(embedding) != 1536:
            raise RuntimeError(f"Invalid embedding dimension: {len(embedding)}")
        
        return embedding
        
    except Exception as e:
        if "Text too short" in str(e):
            raise
        raise RuntimeError(f"Embedding generation failed: {str(e)}")

async def upload_to_pinecone(file_id, filename, embedding, text):
    """Upsert embedding into Pinecone and store the text in metadata."""
    try:
        namespace = generate_namespace(file_id, filename)
        
        response = pinecone_index.upsert(
            vectors=[(str(file_id), embedding, {"filename": filename, "text": text})],
            namespace=namespace
        )
        
        return namespace
        
    except Exception as e:
        raise RuntimeError(f"Pinecone upsert failed: {str(e)}")

async def process_upload(file: UploadFile, file_id=None, content: bytes = None):
    """
    Main pipeline:
    1. Extract text using OpenAI Vision
    2. Generate embedding
    3. Upload to Pinecone
    4. Update Postgres report status
    """
    try:
        if file_id is None:
            file_id = create_file_id()
        
        # Extract text
        text = await extract_text(file, content, is_medical=True)
        
        if not text or not text.strip():
            raise RuntimeError(
                f"No text could be extracted from '{file.filename}'. "
                f"Please ensure the file contains readable text."
            )
        
        text_length = len(text.strip())
        
        if text_length < MIN_TEXT_LENGTH:
            raise RuntimeError(
                f"Insufficient text content in '{file.filename}' "
                f"({text_length} characters, minimum {MIN_TEXT_LENGTH} required)"
            )
        
        # Generate embedding
        embedding = await generate_embedding(text)
        
        # Upload to Pinecone
        namespace = await upload_to_pinecone(file_id, file.filename, embedding, text)
        
        # Update database
        async with AsyncSessionLocal() as session:
            stmt = (
                update(Report)
                .where(Report.report_id == file_id)
                .values(
                    summary={"text_length": len(text), "preview": text[:500]},
                    insights={"namespace": namespace, "extraction_method": "vision_api"},
                    status="completed",
                    uploaded_at=datetime.now(timezone.utc)
                )
            )
            await session.execute(stmt)
            await session.commit()
        
        return file_id
        
    except Exception as e:
        error_msg = str(e)
        
        # Update database with error status
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Report)
                    .where(Report.report_id == file_id)
                    .values(
                        status="failed", 
                        insights={
                            "error": error_msg,
                            "error_type": type(e).__name__,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                )
                await session.commit()
        except Exception:
            pass
        
        raise