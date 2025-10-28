import uuid
from PIL import Image, ImageOps
import pytesseract
from io import BytesIO
import logging

def generate_namespace(file_id: uuid.UUID, filename: str) -> str:
    return f"{file_id}_{filename}"

def create_file_id() -> uuid.UUID:
    return uuid.uuid4()

async def ocr_image(file_bytes: bytes) -> str:
    """
    Extract text from images using pytesseract
    """
    try:
        image = Image.open(BytesIO(file_bytes))
        image = ImageOps.exif_transpose(image)

        if image.mode not in ("L", "RGB"):
            image = image.convert("L")

        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logging.error(f"OCR failed: {e}")
        return ""