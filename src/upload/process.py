import io
import logging
from datetime import datetime, timezone
from fastapi import UploadFile
from sqlalchemy import update
from pypdf import PdfReader
from pdf2image import convert_from_bytes
from database.models.report import Report
from database.settings import AsyncSessionLocal
from .dependency import openai_client, pinecone_index
from .utils import generate_namespace, ocr_image, create_file_id

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Minimum text length required for processing
MIN_TEXT_LENGTH = 20

async def extract_text(file: UploadFile, content: bytes = None) -> str:
    """Extract text from PDF or image. Falls back to OCR if necessary."""
    filename = file.filename.lower()
    if content is None:
        content = await file.read()
        await file.seek(0)
    
    logger.info(f"Extracting text from '{filename}' ({len(content)} bytes)")
    
    # --- PDF Handling ---
    if filename.endswith(".pdf"):
        try:
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            text = ""
            logger.info(f"PDF has {len(reader.pages)} pages")
            
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    logger.info(f"Page {i+1}: extracted {len(page_text)} chars")
                else:
                    logger.info(f"Page {i+1}: no extractable text")
            
            # OCR fallback for scanned PDFs
            if not text.strip():
                logger.info("PDF has no extractable text. Attempting OCR...")
                try:
                    images = convert_from_bytes(content)
                    logger.info(f"Converted PDF to {len(images)} images")
                    ocr_text = ""
                    
                    for i, img in enumerate(images):
                        logger.info(f"OCR processing page {i+1}/{len(images)}")
                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format="PNG")
                        img_bytes.seek(0)
                        
                        try:
                            page_ocr = await ocr_image(img_bytes.getvalue())
                            logger.info(f"Page {i+1} OCR extracted: {len(page_ocr)} chars")
                            ocr_text += page_ocr + "\n"
                        except Exception as page_error:
                            logger.error(f"OCR failed for page {i+1}: {page_error}")
                            continue
                    
                    text = ocr_text
                except Exception as ocr_error:
                    logger.error(f"OCR fallback failed: {ocr_error}", exc_info=True)
                    raise RuntimeError(f"Failed to extract text from PDF: {ocr_error}")
            
            final_text = text.strip()
            logger.info(f"Total extracted text from PDF: {len(final_text)} characters")
            
            if len(final_text) < MIN_TEXT_LENGTH:
                logger.warning(f"Extracted text is short ({len(final_text)} chars): '{final_text[:200]}'")
            
            return final_text
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}", exc_info=True)
            raise RuntimeError(f"PDF processing error: {e}")
    
    # --- Image Handling ---
    elif filename.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif")):
        try:
            logger.info(f"Processing image file: {filename}")
            text = await ocr_image(content)
            logger.info(f"Final OCR result: {len(text)} characters from image '{filename}'")
            
            if len(text) < MIN_TEXT_LENGTH:
                logger.warning(f"Extracted text is short ({len(text)} chars): '{text[:200]}'")
            
            return text
        except Exception as e:
            logger.error(f"Image OCR failed: {e}", exc_info=True)
            raise RuntimeError(f"Image OCR error: {e}")
    
    # --- Unsupported file ---
    else:
        logger.warning(f"Unsupported file type: {filename}")
        raise RuntimeError(f"Unsupported file type: {filename}")

async def generate_embedding(text: str):
    """Generate OpenAI embedding for the given text."""
    try:
        text_length = len(text.strip())
        
        if text_length < MIN_TEXT_LENGTH:
            raise RuntimeError(
                f"Text too short for embedding: {text_length} characters "
                f"(minimum {MIN_TEXT_LENGTH} required). Text: '{text[:100]}...'"
            )
        
        # Truncate to 8000 characters to stay within token limits
        truncated_text = text[:8000]
        logger.info(f"Generating embedding for {len(truncated_text)} characters")
        
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=truncated_text
        )
        embedding = response.data[0].embedding
        
        if len(embedding) != 1536:
            raise RuntimeError(f"Invalid embedding dimension: {len(embedding)}")
        
        logger.info("Embedding generated successfully")
        return embedding
        
    except Exception as e:
        if "Text too short" in str(e):
            raise
        raise RuntimeError(f"OpenAI embedding failed: {e}")

async def upload_to_pinecone(file_id, filename, embedding):
    """Upsert embedding into Pinecone under a unique namespace."""
    try:
        namespace = generate_namespace(file_id, filename)
        logger.info(f"Uploading to Pinecone namespace: {namespace}")
        
        response = pinecone_index.upsert(
            vectors=[(str(file_id), embedding, {"filename": filename})],
            namespace=namespace
        )
        
        if getattr(response, "upserted_count", 0) == 0:
            logger.warning(f"No vectors upserted for namespace {namespace}")
        else:
            logger.info(f"Upserted {response.upserted_count} vector(s) into namespace {namespace}")
        
        return namespace
        
    except Exception as e:
        raise RuntimeError(f"Pinecone upsert failed: {e}")

async def process_upload(file: UploadFile, file_id=None, content: bytes = None):
    """
    Main pipeline:
    1. Extract text
    2. Generate embedding
    3. Upload to Pinecone
    4. Update Postgres report status
    """
    try:
        if file_id is None:
            file_id = create_file_id()
        
        logger.info(f"=== Starting processing for file '{file.filename}' (ID: {file_id}) ===")
        
        # Step 1: Extract text
        logger.info("Step 1: Extracting text...")
        text = await extract_text(file, content)
        
        if not text or not text.strip():
            error_msg = (
                f"No text could be extracted from '{file.filename}'. "
                f"This file appears to contain only images, graphics, or non-readable content. "
                f"Please ensure the file contains readable text and try again."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        text_length = len(text.strip())
        logger.info(f"Successfully extracted {text_length} characters")
        
        # Check if text is too short
        if text_length < MIN_TEXT_LENGTH:
            error_msg = (
                f"Insufficient text content in '{file.filename}' "
                f"({text_length} characters, minimum {MIN_TEXT_LENGTH} required). "
                f"The file may contain mostly images, headers, or very little readable content. "
                f"Text found: '{text[:100]}...'"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Step 2: Generate embedding
        logger.info("Step 2: Generating embedding...")
        embedding = await generate_embedding(text)
        
        # Step 3: Upload embedding to Pinecone
        logger.info("Step 3: Uploading to Pinecone...")
        namespace = await upload_to_pinecone(file_id, file.filename, embedding)
        
        # Step 4: Update Postgres metadata
        logger.info("Step 4: Updating database...")
        async with AsyncSessionLocal() as session:
            stmt = (
                update(Report)
                .where(Report.report_id == file_id)
                .values(
                    summary={"text_length": len(text), "preview": text[:500]},
                    insights={"namespace": namespace},
                    status="completed",
                    uploaded_at=datetime.now(timezone.utc)
                )
            )
            await session.execute(stmt)
            await session.commit()
        
        logger.info(f"=== File '{file.filename}' processed successfully ===")
        return file_id
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"=== Error in process_upload for '{file.filename}': {error_msg} ===", exc_info=True)
        
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
                logger.info("Database updated with error status")
        except Exception as db_error:
            logger.error(f"Failed to update error status in database: {db_error}")
        
        raise