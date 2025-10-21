from fastapi import Request,HTTPException,status,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import user
from database.gets import get_db

async def get_current_user(request:Request,db:AsyncSession=Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not Authenticated'
        )
    result = await db.execute(select(user.User).where(user.User.user_id==user_id))
    db_user = result.scalars().one_or_none()

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User Not Found'
        )

    return db_user