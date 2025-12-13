import uuid
import base64
from io import BytesIO
from PIL import Image, ImageOps, ImageEnhance
from openai import OpenAI
import config

openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

def generate_namespace(file_id: uuid.UUID, filename: str) -> str:
    """Generate a unique namespace for Pinecone."""
    return f"{file_id}_{filename}"

def create_file_id() -> uuid.UUID:
    """Generate a unique UUID for a file/report."""
    return uuid.uuid4()

def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    try:
        buffered = BytesIO()
        image.save(buffered, format=format)
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Failed to convert image to base64: {str(e)}")

def enhance_image_for_ocr(image: Image.Image) -> Image.Image:
    """Enhance image quality for better OCR results."""
    try:
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        return image
    except Exception:
        return image

async def ocr_image(file_bytes: bytes, is_medical_document: bool = True) -> str:
    """
    Extract text from an image using OpenAI Vision API.
    Enhanced for handwritten medical prescriptions and documents.
    """
    try:
        # Load and prepare image
        image = Image.open(BytesIO(file_bytes))
        image = ImageOps.exif_transpose(image)
        image = enhance_image_for_ocr(image)
        
        # Resize if too large
        max_dimension = 2000
        width, height = image.size
        if width > max_dimension or height > max_dimension:
            scale = min(max_dimension / width, max_dimension / height)
            new_size = (int(width * scale), int(height * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to base64
        img_format = "PNG"
        base64_image = image_to_base64(image, format=img_format)
        
        # Choose prompt based on document type
        if is_medical_document:
            extraction_prompt = """You are an expert medical transcriptionist. Extract ALL text from this medical document image.

IMPORTANT INSTRUCTIONS:
1. This may contain HANDWRITTEN text - read it carefully, even if messy
2. Extract EVERY piece of information including:
   - Patient details (name, age, sex, address, date)
   - Doctor/Physician information (name, license numbers)
   - Prescription details (Rx section):
     * Medicine names (even if partially legible)
     * Dosages (e.g., 500mg)
     * Instructions (e.g., "1 cap 3x a day", "Sig:")
   - Any printed or stamped text
   - Any signatures or illegible marks (note as [signature] or [illegible])
3. Preserve the document structure:
   - Use headers like "Patient Information:", "Prescription:", "Doctor Details:"
   - Keep line breaks to maintain readability
   - If something is unclear, make your best attempt and note it like [possibly: text]
4. For handwritten text:
   - Take your time to decipher each letter
   - Common medical abbreviations: Rx (prescription), Sig (directions), Cap (capsule), Tab (tablet)
   - Look at context clues from other words

Return ONLY the extracted text in a clear, organized format. Do not add explanations."""
        else:
            extraction_prompt = """Extract all visible text from this image. 
Return ONLY the extracted text, preserving the layout and formatting as much as possible.
If there are tables, preserve their structure.
Pay special attention to handwritten text - decode it carefully.
Do not add any explanations or descriptions."""
        
        # Call OpenAI Vision API
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": extraction_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{img_format.lower()};base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0.1
        )
        
        text = response.choices[0].message.content.strip()
        return text if text else ""
        
    except Exception as e:
        raise RuntimeError(f"OCR processing error: {str(e)}")