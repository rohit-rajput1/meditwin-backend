import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DB_USER_NAME=os.getenv("DB_USER_NAME")
DB_PASSWORD=os.getenv("DB_PASSWORD")
DB_HOST=os.getenv("DB_HOST")
DB_PORT=os.getenv("DB_PORT")
DB_NAME=os.getenv("DB_NAME")

# Session Configuration
SECRET_KEY=os.getenv("SECRET_KEY")
SESSION_COOKIE=os.getenv("SESSION_COOKIE")
SESSION_MAX_AGE=os.getenv("SESSION_MAX_AGE")

DATABASE_URL=(
    f"postgresql+psycopg2://{DB_USER_NAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

