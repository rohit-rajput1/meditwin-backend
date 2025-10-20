"""
Provides an async database session generator for dependency injection.

- Uses AsyncSessionLocal from the database setup.
- Handles commit, rollback, and session cleanup automatically.
- Can be used in async frameworks like FastAPI as a dependency.
"""

from database.settings import AsyncSessionLocal

async def get_db():
    """
    Async generator to provide a database session.

    Usage:
        async for session in get_db():
            ...
    """
    async with AsyncSessionLocal() as session:  # Open async session
        try:
            yield session  # Provide session to caller
            await session.commit()  # Commit if no exceptions
        except Exception as e:
            await session.rollback()  # Rollback on error
            raise
        finally:
            await session.close()  # Ensure session is closed
