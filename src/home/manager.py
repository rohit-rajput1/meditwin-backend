from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models.report_type import ReportType
from typing import List,Tuple
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from database.models import *
from sqlalchemy import func, asc, desc
from src.upload.dependency import pinecone_index

async def get_all_report_types(db: AsyncSession) -> ReportType:
    """
    Fetch all report types from the database.
    """
    try:
        result = await db.execute(select(ReportType))
        report_types = result.scalars().all()
        return report_types
    except SQLAlchemyError as e:
        raise Exception(f"Database error while fetching report types: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error while fetching report types: {str(e)}")

async def get_all_reports(
    db: AsyncSession,
    user_id: UUID,   # ⬅ added
    search: str | None,
    sort: str | None,
    page: int,
    limit: int,
    report_type_name: str | None,
    status: str | None
):
    try:
        query = (
            select(Report)
            .join(Report.report_type)
            .options(selectinload(Report.report_type))
        )

        # USER FILTER (MOST IMPORTANT)
        query = query.where(Report.user_id == user_id)

        # FILTER: report_type_name
        if report_type_name:
            query = query.where(
                func.lower(ReportType.name) == report_type_name.lower()
            )

        # FILTER: status
        if status:
            query = query.where(Report.status == status.lower())

        # SEARCH
        if search:
            search_term = f"%{search.lower()}%"
            query = query.where(
                Report.report_name.ilike(search_term) |
                ReportType.name.ilike(search_term)
            )

        # COUNT BEFORE PAGINATION
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        # SORT
        if sort == "asc":
            query = query.order_by(asc(Report.uploaded_at))
        else:
            query = query.order_by(desc(Report.uploaded_at))

        # PAGINATION
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        data = (await db.execute(query)).scalars().all()
        return data, total

    except Exception as e:
        raise Exception(f"Error fetching reports: {str(e)}")

async def update_report_name(db: AsyncSession, report_id, new_name):
    try:
        query = select(Report).where(Report.report_id == report_id)
        result = await db.execute(query)
        report = result.scalar_one_or_none()

        if not report:
            return None  # handled in views

        report.report_name = new_name
        await db.commit()
        await db.refresh(report)

        return report

    except SQLAlchemyError as e:
        await db.rollback()
        raise Exception(f"DB error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise Exception(f"Unexpected error: {str(e)}")
    
async def delete_report(db: AsyncSession, report_id: UUID):
    try:
        # 1. Fetch the report
        result = await db.execute(
            select(Report).where(Report.report_id == report_id)
        )
        report = result.scalar_one_or_none()

        if not report:
            return None

        deleted_report_name = report.report_name

        # 2. Delete Pinecone namespace (if saved)
        try:
            namespace = None
            if report.insights and "namespace" in report.insights:
                namespace = report.insights["namespace"]

            if namespace:
                pinecone_index.delete(delete_all=True, namespace=namespace)
                print(f"Deleted Pinecone namespace: {namespace}")

        except Exception as e:
            # Do NOT cancel deletion — log & continue
            print(f"[WARN] Pinecone namespace deletion failed: {str(e)}")

        # 3. Invalidate chats linked to this report
        chat_result = await db.execute(
            select(Chat).where(Chat.file_id == report_id)
        )
        chat_items = chat_result.scalars().all()
        for chat in chat_items:
            chat.is_valid_chat = False

        # 4. Delete dashboard if exists
        dashboard_result = await db.execute(
            select(Dashboard).where(Dashboard.report_id == report_id)
        )
        dashboard = dashboard_result.scalar_one_or_none()
        if dashboard:
            await db.delete(dashboard)

        # 5. Delete the report
        await db.delete(report)

        # Commit DB changes
        await db.commit()

        return {
            "report_id": report_id,
            "report_name": deleted_report_name,
            "message": "Report deleted successfully (including Pinecone namespace)"
        }

    except SQLAlchemyError as e:
        await db.rollback()
        raise Exception(f"Database error: {str(e)}")

    except Exception as e:
        await db.rollback()
        raise Exception(f"Unexpected error: {str(e)}")
