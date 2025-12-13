import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DB_USER_NAME = os.getenv("DB_USER_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))  # Ensure port is integer
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER_NAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Session Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
SESSION_COOKIE = os.getenv("SESSION_COOKIE")
SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE", 3600))

# AI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Pinecone Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
