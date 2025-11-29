from fastapi import APIRouter, Depends, HTTPException,Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from database.gets import get_db
from src.auth.dependency import get_current_user
from .schema import CreateChatRequest, CreateChatResponse,RecentChatResponse,ChatHistory,ChatHistoryResponse,ContinueChatRequest,MessageResponse,RenameChatRequest,ChatDeleteRequest
from .manager import create_chat,recent_chat,chat_history,continue_chat,rename_chat,delete_chat
from typing import Optional

chat_router = APIRouter(tags=["Chat"])

@chat_router.post("/create-chat", response_model=CreateChatResponse)
async def create_chat_api(
    payload: CreateChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        result = await create_chat(
            file_id=payload.file_id,
            user_id=current_user.user_id,
            db=db
        )

        return CreateChatResponse(
            file_id=result["file_id"],
            chat_id=result["chat_id"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Chat creation failed: {str(e)}")
    
@chat_router.post("/continue-chat", response_model=MessageResponse)
async def continue_chat_api(
    payload: ContinueChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = current_user.user_id
    msg = await continue_chat(payload, db,user_id)
    return msg
    
@chat_router.post("/chat-history/{chat_id}",response_model=ChatHistoryResponse)
async def chat_history_api(
    chat_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        history = await chat_history(db, chat_id)
        return history
    
    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@chat_router.post("/rename-chat")
async def rename_chat_api(
    payload: RenameChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await rename_chat(
        db=db,
        user_id=current_user.user_id,
        chat_id=payload.chat_id,
        chat_name=payload.chat_name
    )


@chat_router.post("/recent-chat",response_model=RecentChatResponse)
async def recent_chat_api(
    db:AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    search:Optional[str]=Query(None,description="Search Chat by Chat Name")
):
    try:
        user_id = current_user.user_id
        chats = await recent_chat(db,user_id,search)
        return {"chats": chats}
    except ValueError as e:
        raise HTTPException(status_code=404,detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Error fetching chat history: {str(e)}")

@chat_router.delete("/delete-chat")
async def delete_chat_api(
    data: ChatDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        return await delete_chat(db, data.chat_id)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
