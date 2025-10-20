"""
Sets up an asynchronous connection to a PostgreSQL database using SQLAlchemy.

- Loads DB credentials from environment/config.
- Creates an async engine for non-blocking DB operations.
- Provides AsyncSessionLocal to use in async functions for database access.
"""

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import config

# Load environment variables
load_dotenv()

# DB configuration
db_username = config.DB_USER_NAME
db_password = config.DB_PASSWORD
db_host = config.DB_HOST
db_port = config.DB_PORT
db_name = config.DB_NAME

# PostgreSQL database URL
database_url = f"postgresql+asyncpg://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"

# Create async engine (echo=True logs SQL queries)
engine = create_async_engine(database_url, echo=False)

# Async session maker
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
