from pydantic import BaseModel
from uuid import UUID
from typing import List,Optional
from datetime import datetime

class CreateChatRequest(BaseModel):
    file_id: UUID

class CreateChatResponse(BaseModel):
    file_id: UUID
    chat_id: UUID

class ContinueChatRequest(BaseModel):
    chat_id: UUID
    user_query: str

class MessageResponse(BaseModel):
    chat_id: UUID
    user_query: str
    bot_response: str
    created_at: datetime

class ChatHistory(BaseModel):
    message_id: UUID
    user_query: str
    bot_response: str
    metadatas: dict
    created_at: datetime

    class Config:
        orm_mode = True

class ChatHistoryResponse(BaseModel):
    chat_id:UUID
    file_id:Optional[UUID]
    is_valid_chat: bool
    messages: List[ChatHistory]

class RecentChatItem(BaseModel):
    chat_id:UUID
    chat_name:str
    is_valid_chat: bool

class RecentChatResponse(BaseModel):
    chats:List[RecentChatItem]

class RenameChatRequest(BaseModel):
    chat_id: UUID
    chat_name: str

class ChatDeleteRequest(BaseModel):
    chat_id: UUID