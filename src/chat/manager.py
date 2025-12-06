from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func,delete,update
from fastapi import HTTPException
from uuid import UUID,uuid4
from database.models.chat import Chat
from database.models.report import Report
from database.models.message import Message
from database.models.report_type import ReportType
from .utils import build_prompt
from openai import AsyncOpenAI
import config

client = AsyncOpenAI(api_key=config.OPENAI_KEY) 

async def create_chat(db: AsyncSession, user_id: UUID, file_id: UUID):
    try:
        result = await db.execute(select(Report).where(Report.report_id == file_id))
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        new_chat = Chat(
            chat_id=uuid4(),
            created_by=user_id,
            file_id=file_id,
            chat_name="Untitled Chat",
            is_valid_chat=True
        )

        db.add(new_chat)
        await db.flush()
        await db.refresh(new_chat)
        await db.commit()

        return {
            "chat_id": new_chat.chat_id,
            "file_id": file_id
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error Creating Chat: {str(e)}")

async def continue_chat(data, db: AsyncSession, user_id: UUID):
    chat = await db.get(Chat, data.chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    if not chat.is_valid_chat:
        raise HTTPException(400, "This chat is no longer valid")

    report = await db.get(Report, chat.file_id)
    if not report:
        raise HTTPException(404, "Report not found")

    if not report.is_valid_report:
        raise HTTPException(400, "This report is no longer valid")

    report_type = await db.get(ReportType, report.report_type_id)

    analysis = report.insights.get("analysis", {})

    report_data = {
        "summary": report.summary,
        "key_findings": report.key_findings,
        "recommendations": report.recommendations,
        "insights": analysis.get("insights"),
    }

    # Fetch chat messages
    history_result = await db.execute(
        select(Message).where(Message.chat_id == chat.chat_id).order_by(Message.created_at.asc())
    )
    chat_history = history_result.scalars().all()

    messages = build_prompt(
        report_type_name=report_type.name,
        report_data=report_data,
        chat_history=chat_history,
    )

    messages.append({"role": "user", "content": data.user_query})

    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
    )
    bot_answer = response.choices[0].message.content

    if chat.chat_name == "Untitled Chat":
        chat.chat_name = data.user_query

    msg = Message(
        chat_id=chat.chat_id,
        user_id=user_id,
        user_query=data.user_query,
        bot_response=bot_answer,
        metadatas={}
    )

    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return msg

async def chat_history(db: AsyncSession, chat_id: UUID):
    chat = await db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(404, detail="Chat not found")

    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()

    return {
        "chat_id": chat_id,
        "file_id": chat.file_id,
        "is_valid_chat": chat.is_valid_chat,
        "messages": messages
    }

async def recent_chat(db: AsyncSession, user_id: UUID, search: str = None):

    query = select(Chat.chat_id, Chat.chat_name, Chat.is_valid_chat).where(
        Chat.created_by == user_id
    )

    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(func.lower(Chat.chat_name).ilike(search_term))

    query = query.order_by(Chat.created_at.desc())
    result = await db.execute(query)
    chats = result.all()

    return [
        {
            "chat_id": c.chat_id,
            "chat_name": c.chat_name,
            "is_valid_chat": c.is_valid_chat
        }
        for c in chats
    ]

async def rename_chat(db: AsyncSession, user_id: UUID, chat_id: UUID, chat_name: str):
    chat = await db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(404, detail="Chat not found")

    if chat.created_by != user_id:
        raise HTTPException(403, detail="Unauthorized")

    chat.chat_name = chat_name
    await db.commit()
    await db.refresh(chat)

    return {
        "chat_id": chat.chat_id,
        "chat_name": chat.chat_name
    }

async def delete_chat(db: AsyncSession, chat_id: UUID):

    chat = await db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(404, detail="Chat not found")

    # Soft delete the chat
    chat.is_valid_chat = False

    # Soft delete all messages
    await db.execute(
        update(Message)
        .where(Message.chat_id == chat_id)
        .values(is_valid=False)
    )

    await db.commit()

    return {"message": "Chat deleted", "chat_id": chat_id}
