from fastapi import APIRouter,Depends,status,Request,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from . import manager
from . import schema
from .dependency import get_current_user
from database.gets import get_db

auth = APIRouter(tags=['Auth'])

@auth.post('/login')
async def login(request: Request, user: schema.UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        return await manager.login_user(request, user.user_email, user.password, db)
    except HTTPException:
        # Re-raise known HTTP exceptions (like invalid credentials)
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during login: {str(e)}"
        )

@auth.post('/logout')
async def logout(request: Request):
    try:
        return await manager.logout_user(request)
    except HTTPException:
        # Re-raise known HTTP exceptions if any
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during logout: {str(e)}"
        )

@auth.post('/register', response_model=schema.UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: schema.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register endpoint — expects user_email and password.
    """
    try:
        new_user = await manager.register_user(user.user_email, user.password, db)
        return new_user

    except HTTPException:
        # Raise HTTPExceptions from manager as-is
        raise

    except Exception as e:
        # Catch all unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {str(e)}"
        )
    
@auth.post("/profile-info",response_model=schema.UserProfileResponse,status_code=status.HTTP_200_OK)
async def add_profile_info(
    profile_data: schema.UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update or add profile info for the currently logged-in user.
    Only the logged-in user can update their profile.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )

    try:
        profile = await manager.add_or_update_user_profile(current_user.user_id, profile_data, db)
        return profile
    except SQLAlchemyError as e:
        # Database-specific errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(e)}"
        )
    except Exception as e:
        # Catch-all for other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error occurred: {str(e)}"
        )

@auth.get("/profile-info",response_model=schema.UserProfileResponse,status_code=status.HTTP_200_OK)
async def get_profile_info(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get the profile info for the currently logged-in user.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )

    try:
        profile = await manager.get_user_profile(current_user.user_id, db)

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Please create your profile first."
            )

        return profile

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error occurred: {str(e)}"
        )

@auth.post("/health-info",response_model=schema.HealthInfoResponse,status_code=status.HTTP_200_OK)
async def add_health_info(
    health_data: schema.HealthInfoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Add or update health info for the currently logged-in user.
    Only the logged-in user can add/update their health info.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )

    try:
        health_info = await manager.add_or_update_health_info(current_user.user_id, health_data, db)
        return health_info
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error occurred: {str(e)}"
        )
    
@auth.get("/me")
async def get_current_user_info(
    current_user=Depends(get_current_user)
):
    """Get current authenticated user information"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    return {
        "user_id": current_user.user_id,
        "email": current_user.user_email,  
    }