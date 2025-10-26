from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from database.settings import engine
from database.models import *
import config
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from src.upload.handler import rate_limit_handler

# Import Routers
from src.auth import views as auth_views
from src.home import views as home_views
from src.upload import views as upload_views

app = FastAPI(
    title="Meditwin Backend",
    version="1.0.0",
    description="This is the Backend API Page for the Meditwin Application",
    openapi_version="3.0.3"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    session_cookie=config.SESSION_COOKIE,
    max_age=int(config.SESSION_MAX_AGE)
)

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Use your custom handler instead of private SlowAPI handler
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Auth Routes
app.include_router(auth_views.auth,prefix="/auth")

# Home Routes
app.include_router(home_views.report_router,prefix="/report")

# Upload Routes
app.include_router(upload_views.upload_router,prefix="/upload")

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