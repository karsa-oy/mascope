from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from backend.db import db_path

# Database configuration
DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def test_database_connection():
    try:
        # create a new session and close it
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        print("Database connection established successfully.")
    except Exception as e:
        print("Error while establishing the database connection: ", e)


async def init_db():
    await test_database_connection()
