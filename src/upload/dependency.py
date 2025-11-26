from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.report_type import ReportType
from openai import OpenAI
from pinecone import Pinecone
from slowapi import Limiter
from slowapi.util import get_remote_address
import config

# OpenAI Initialization
openai_client = OpenAI(api_key=config.OPENAI_KEY)

# Pinecone Initialization
pinecone_client = Pinecone(api_key=config.PINECONE_API_KEY)
pinecone_index_name = config.PINECONE_INDEX_NAME
EMBEDDING_DIMENSION = 1536
EMBEDDING_MODEL = "text-embedding-3-small"

# Create index if not exists
try:
    if not pinecone_client.has_index(pinecone_index_name):
        pinecone_client.create_index(
            name=pinecone_index_name,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec={"serverless": {"cloud": "aws", "region": "us-east-1"}}
        )
except Exception as e:
    raise RuntimeError(f"Failed to initialize Pinecone index: {e}")

# Connect to the index
pinecone_index = pinecone_client.Index(pinecone_index_name)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Helper Functions
async def get_report_type(db: AsyncSession, report_type_id: str):
    try:
        report_type = await db.get(ReportType, report_type_id)
        if not report_type:
            raise HTTPException(status_code=404, detail="Report type not found")
        return report_type
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch report type")

def allowed_file(filename: str): 
    allowed_extensions = ["pdf", "jpeg", "jpg", "png"] 
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions