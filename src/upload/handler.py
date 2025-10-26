from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )