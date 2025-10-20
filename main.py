from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from database.settings import engine
from database.models import *
import config
# Add Auth Routers Here


app = FastAPI(
    title="Meditwin Backend",
    version="1.0.0",
    description="This is the Backend API Page for the Meditwin Application",
    openapi_version="3.0.3"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    session_cookie=config.SESSION_COOKIE,
    max_age=config.SESSION_MAX_AGE
)

@app.get('/')
async def root():
    return {"message": 'Hi Dear, Why are you here? Go to "localhost:8000/docs"'}

@app.get("/health")
async def health_check():
    return {"status":"Healthy","version":"1.0.0"}

@app.on_event("startup")
async def startup_event():
    # Async Table creation
    from database.base import Base
    from sqlalchemy.ext.asyncio import AsyncEngine

    if isinstance(engine,AsyncEngine):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)