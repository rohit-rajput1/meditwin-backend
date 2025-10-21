from datetime import datetime, timezone
from fastapi import Request,HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from .utils import verify_password,hash_password
from database.models import user
from database.models.profile_info import UserProfile
from database.models.health_info import HealthInfo
from . import schema

async def login_user(request: Request, email: str, password: str, db: AsyncSession):
    try:
        result = await db.execute(select(user.User).where(user.User.user_email == email))
        db_user = result.scalars().one_or_none()

        if not db_user or not verify_password(password, db_user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        request.session["user_id"] = str(db_user.user_id)
        return {"message": "Login Successful"}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
async def register_user(user_name: str, user_email: str, password: str, db: AsyncSession):
    try:
        # Check if the user already exists
        result = await db.execute(select(user.User).where(user.User.user_email == user_email))
        existing_user = result.scalars().first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash the password and create new user
        hashed_password = hash_password(password)
        new_user = user.User(
            user_name=user_name,
            user_email=user_email,
            hashed_password=hashed_password
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return new_user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {str(e)}"
        )
    
async def add_or_update_user_profile(user_id: str, data: schema.UserProfileUpdate, db: AsyncSession) -> UserProfile:
    """
    Add or update the profile info for the currently logged-in user.
    Wrapped in try-except to handle DB errors.
    """
    try:
        # Check if profile exists
        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.scalars().first()

        if profile:
            # Update existing profile
            profile.first_name = data.first_name
            profile.last_name = data.last_name
            profile.phone = data.phone
            profile.location = data.location
            profile.date_of_birth = data.date_of_birth
            profile.updated_at = datetime.now(timezone.utc)
        else:
            # Create profile if it does not exist
            profile = UserProfile(
                user_id=user_id,
                first_name=data.first_name,
                last_name=data.last_name,
                phone=data.phone,
                location=data.location,
                date_of_birth=data.date_of_birth,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(profile)

        await db.commit()
        await db.refresh(profile)
        return profile

    except SQLAlchemyError as e:
        await db.rollback()
        # Optionally, log the error here
        raise Exception(f"Database error occurred while adding/updating profile: {str(e)}")

    except Exception as e:
        # Catch-all for other errors
        raise Exception(f"Unexpected error occurred while adding/updating profile: {str(e)}")
    
async def add_or_update_health_info(user_id: str, data: schema.HealthInfoUpdate, db: AsyncSession) -> HealthInfo:
    """
    Add or update the health info for the currently logged-in user.
    """
    try:
        # Check if health info exists
        result = await db.execute(select(HealthInfo).where(HealthInfo.user_id == user_id))
        health_info = result.scalars().first()

        if health_info:
            # Update existing health info
            health_info.height_cm = data.height_cm
            health_info.weight_kg = data.weight_kg
            health_info.blood_type = data.blood_type
            health_info.emergency_contact = data.emergency_contact
            health_info.allergies = data.allergies
            health_info.current_medications = data.current_medications
            health_info.updated_at = datetime.now(timezone.utc)
        else:
            # Create new health info if it does not exist
            health_info = HealthInfo(
                user_id=user_id,
                height_cm=data.height_cm,
                weight_kg=data.weight_kg,
                blood_type=data.blood_type,
                emergency_contact=data.emergency_contact,
                allergies=data.allergies,
                current_medications=data.current_medications,
                updated_at=datetime.now(timezone.utc)
            )
            db.add(health_info)

        await db.commit()
        await db.refresh(health_info)
        return health_info

    except SQLAlchemyError as e:
        await db.rollback()
        raise Exception(f"Database error: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error: {str(e)}")


async def logout_user(request: Request):
    try:
        request.session.clear()
        return {"message": "Logout Successful"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error logging out: {str(e)}"
        )