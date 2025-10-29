import uuid
import logging
from io import BytesIO
from PIL import Image, ImageOps, ImageEnhance
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy initialization of PaddleOCR to avoid startup issues
_ocr_engine = None

def get_ocr_engine():
    """Lazy initialization of PaddleOCR engine."""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            logger.info("Initializing PaddleOCR engine...")
            # Initialize with minimal parameters - newer versions don't support show_log or use_gpu
            _ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')
            logger.info("PaddleOCR engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}", exc_info=True)
            raise RuntimeError(f"PaddleOCR initialization failed: {e}")
    return _ocr_engine

def generate_namespace(file_id: uuid.UUID, filename: str) -> str:
    """Generate a unique namespace for Pinecone."""
    return f"{file_id}_{filename}"

def create_file_id() -> uuid.UUID:
    """Generate a unique UUID for a file/report."""
    return uuid.uuid4()

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Preprocess image to improve OCR accuracy."""
    # Convert to RGB if needed
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    
    # Resize small images for better OCR
    width, height = image.size
    if width < 1000 or height < 1000:
        scale = max(1000 / width, 1000 / height)
        new_size = (int(width * scale), int(height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        logger.info(f"Resized image from {width}x{height} to {new_size[0]}x{new_size[1]}")
    
    # Enhance contrast for better text detection
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.5)
    
    return image

async def ocr_image(file_bytes: bytes) -> str:
    """
    Extract text from an image using PaddleOCR.
    Supports PNG, JPG, JPEG, etc.
    """
    try:
        # Get OCR engine (lazy initialization)
        ocr_engine = get_ocr_engine()
        
        # Load and prepare image
        image = Image.open(BytesIO(file_bytes))
        logger.info(f"Image loaded: mode={image.mode}, size={image.size}")
        
        image = ImageOps.exif_transpose(image)
        
        # Try OCR on original image first (without preprocessing)
        img_np_original = np.array(image.convert("RGB"))
        logger.info("Attempting OCR on original image...")
        
        # Call OCR without cls parameter for newer versions
        result = ocr_engine.ocr(img_np_original)
        
        # If no results, try with preprocessing
        if not result or not result[0]:
            logger.info("No text detected on original image, trying with preprocessing...")
            image_processed = preprocess_image_for_ocr(image)
            img_np_processed = np.array(image_processed)
            result = ocr_engine.ocr(img_np_processed)
        
        # Parse results with intelligent text reconstruction
        text_lines = []
        if result and result[0]:
            logger.info(f"OCR detected {len(result[0])} text boxes")
            
            for idx, line in enumerate(result[0]):
                if line and len(line) >= 2:
                    detected_text = line[1][0].strip()
                    confidence = line[1][1] if len(line[1]) > 1 else 0.0
                    
                    if detected_text:
                        text_lines.append(detected_text)
                        logger.debug(f"Box {idx}: '{detected_text}' (confidence: {confidence:.2f})")
        
        if not text_lines:
            logger.warning("No text detected by OCR")
            logger.warning(f"Image info: size={image.size}, mode={image.mode}")
            return ""
        
        # Smart text joining logic
        # Check if most lines are single characters (indicates poor OCR)
        single_char_count = sum(1 for t in text_lines if len(t) == 1)
        avg_length = sum(len(t) for t in text_lines) / len(text_lines) if text_lines else 0
        
        logger.info(f"OCR stats: {len(text_lines)} boxes, {single_char_count} single chars, avg length: {avg_length:.1f}")
        
        if single_char_count > len(text_lines) * 0.7 or avg_length < 2:
            # Mostly single characters - join with space
            text = " ".join(text_lines).strip()
            logger.info("Character-by-character detection - joining with spaces")
        else:
            # Normal text detection - preserve line breaks
            text = "\n".join(text_lines).strip()
            logger.info("Normal text detection - preserving line breaks")
        
        logger.info(f"OCR extracted {len(text)} characters total")
        if text:
            logger.info(f"Text preview: '{text[:100]}...'")
        
        return text
        
    except Exception as e:
        logger.error(f"OCR failed: {e}", exc_info=True)
        # Re-raise with more context
        raise RuntimeError(f"OCR processing error: {e}")