from .dependency import openai_client, pinecone_index
from .utils import generate_namespace, ocr_image, create_file_id
from pypdf import PdfReader
from fastapi import UploadFile
import io

async def extract_text(file: UploadFile, content: bytes = None) -> str:
    """
    Extract text from file. If content is provided, use it; otherwise read from file.
    """
    filename = file.filename
    ext = filename.lower()

    if content is None:
        content = await file.read()
        await file.seek(0)

    if ext.endswith(".pdf"):
        try:
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except Exception as e:
            print(f"PDF extraction failed: {e}")
            return ""
        
    elif ext.endswith(("jpg", "jpeg", "png")):
        return await ocr_image(content)
    
    else:
        return ""
    
async def generate_embedding(text: str):
    """
    Generate Embedding using OpenAI with text-embedding-3-small (1536 dimensions)
    """
    try:
        # Use text-embedding-3-small which returns 1536 dimensions
        model_to_use = "text-embedding-3-small"
        print(f"Generating embedding with model: {model_to_use}")
        
        response = openai_client.embeddings.create(
            model=model_to_use,
            input=text[:8000]
        )
        
        embedding = response.data[0].embedding
        print(f"Generated embedding with {len(embedding)} dimensions (expected: 1536)")
        
        # Verify dimension
        if len(embedding) != 1536:
            raise RuntimeError(f"Wrong embedding dimension! Got {len(embedding)}, expected 1536")
        
        return embedding
    except Exception as e:
        raise RuntimeError(f"OpenAI embedding failed: {e}")
    
async def upload_to_pinecone(file_id, filename, embedding):
    """
    Upload embedding to Pinecone Index
    """
    try:
        namespace = generate_namespace(file_id, filename)
        print(f"Uploading to Pinecone - Embedding dimension: {len(embedding)}")
        pinecone_index.upsert(
            vectors=[(str(file_id), embedding, {"filename": filename})],
            namespace=namespace
        )
        print(f"Successfully uploaded to Pinecone: {file_id} in namespace {namespace}")
    except Exception as e:
        print(f"Pinecone upload error details: {e}")
        raise RuntimeError(f"Pinecone upload failed: {e}")
    
async def process_upload(file: UploadFile, file_id=None, content: bytes = None):
    """
    Full pipeline: extract text -> generate embedding -> upload to Pinecone
    """
    try:
        if file_id is None:
            file_id = create_file_id()
        
        print(f"Processing file: {file.filename} with ID: {file_id}")
        
        # Extract text
        text = await extract_text(file, content)
        
        if not text or not text.strip():
            raise RuntimeError("No text extracted from file")
        
        print(f"Extracted {len(text)} characters of text")
        
        # Generate embedding
        embedding = await generate_embedding(text)
        
        # Upload to Pinecone
        await upload_to_pinecone(file_id, file.filename, embedding)
        
        print(f"Successfully processed file: {file.filename}")
        return file_id
    except Exception as e:
        print(f"Error in process_upload: {e}")
        raise