from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func,delete
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
    """
    Create a new chat linked with a report (file_id).
    """
    try:
        # Validate report exists
        result = await db.execute(
            select(Report).where(Report.report_id == file_id)
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        # Create chat
        new_chat = Chat(
            chat_id=uuid4(),
            created_by=user_id,
            file_id=file_id,
            chat_name="Untitled Chat"
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
        raise HTTPException(
            status_code=500,
            detail=f"Error Creating Chat: {str(e)}"
        )

async def continue_chat(data, db: AsyncSession, user_id: UUID):
    """
    Continue chat using the ANALYZED medical data.
    LLM will now understand the uploaded file.
    """

    # 1. Fetch chat
    chat = await db.get(Chat, data.chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    # 2. Fetch the linked report
    report = await db.get(Report, chat.file_id)
    if not report:
        raise HTTPException(404, "Report not found")

    # 3. Fetch report type
    report_type = await db.get(ReportType, report.report_type_id)

    # 4. Fetch stored analysis from report.insights
    analysis = report.insights.get("analysis", {})

    # build a minimal, clean dict to feed prompt
    report_data = {
        "summary": report.summary,
        "key_findings": report.key_findings,
        "recommendations": report.recommendations,
        "insights": analysis.get("insights"),
    }

    # 5. Fetch chat history
    query = (
        select(Message)
        .where(Message.chat_id == chat.chat_id)
        .order_by(Message.created_at.asc())
    )
    history_result = await db.execute(query)
    chat_history = history_result.scalars().all()

    # 6. Build full OpenAI prompt with REPORT DATA
    messages = build_prompt(
        report_type_name=report_type.name,
        report_data=report_data,
        chat_history=chat_history,
    )

    # 7. Add user query
    messages.append({"role": "user", "content": data.user_query})

    # 8. Send to OpenAI
    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
    )
    bot_answer = response.choices[0].message.content

    # 9A. Update chat_name only for the first message
    if chat.chat_name == "Untitled Chat":
        chat.chat_name = data.user_query  # update with first question

    # 9B. Store user query + bot response
    message = Message(
        chat_id=chat.chat_id,
        user_id=user_id,
        user_query=data.user_query,
        bot_response=bot_answer,
        metadatas={}
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    return message

async def chat_history(db: AsyncSession, chat_id: UUID):
    chat_result = await db.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat = chat_result.scalar_one_or_none()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Fetch messages
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
    )

    messages = result.scalars().all()

    return {
        "chat_id": chat_id,
        "file_id": chat.file_id, 
        "messages": messages
    }


async def recent_chat(db:AsyncSession,user_id:UUID,search:str=None):
    query = select(Chat.chat_id,Chat.chat_name).where(Chat.created_by == user_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(func.lower(Chat.chat_name).ilike(search_term))

    query = query.order_by(Chat.created_at.desc())
    result = await db.execute(query)
    chats =  result.all()

    return [
        {
            "chat_id": chat.chat_id,
            "chat_name":chat.chat_name
        }
        for chat in chats
    ]

async def rename_chat(db: AsyncSession, user_id: UUID, chat_id: UUID, chat_name: str):
    try:
        # 1. Fetch chat
        chat = await db.get(Chat, chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        # 2. Check ownership
        if chat.created_by != user_id:
            raise HTTPException(
                status_code=403,
                detail="User not authorized to rename this chat"
            )

        # 3. Update chat_name
        chat.chat_name = chat_name

        # 4. Commit changes
        await db.commit()
        await db.refresh(chat)

        return {
            "chat_id": chat.chat_id,
            "chat_name": chat.chat_name,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error Renaming Chat: {str(e)}"
        )

async def delete_chat(db: AsyncSession, chat_id: UUID):
    """
    Delete a chat and all messages belonging to it.
    """
    try:
        # 1. Fetch chat
        chat = await db.get(Chat, chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        # 2. Delete all messages under the chat
        await db.execute(
            delete(Message).where(Message.chat_id == chat_id)
        )

        # 3. Delete the chat
        await db.delete(chat)

        # 4. Commit
        await db.commit()

        return {
            "message": "Chat deleted successfully",
            "chat_id": chat_id
        }

    except HTTPException:
        raise

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error Deleting Chat: {str(e)}"
        )
