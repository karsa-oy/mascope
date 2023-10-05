from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select

from backend.db_api_rest import async_session
from ..models.models import AttributeTemplate


async def get_attribute_templates(sort: str, order: str, page: int, limit: int):
    async with async_session() as session:
        stmt = select(AttributeTemplate)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(AttributeTemplate, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(AttributeTemplate, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        attribute_templates = result.scalars().all()

        return {
            "results": total,
            "data": [
                attribute_template.to_dict()
                for attribute_template in attribute_templates
            ],
        }


async def get_attribute_template_by_id(attribute_template_id: str):
    async with async_session() as session:
        stmt = select(AttributeTemplate).filter(
            AttributeTemplate.attribute_template_id == attribute_template_id
        )
        result = await session.execute(stmt)
        attribute_template = result.scalars().first()

        if not attribute_template:
            raise HTTPException(
                status_code=404,
                detail=f"AttributeTemplate with ID {attribute_template_id} not found",
            )

        return attribute_template.to_dict()
