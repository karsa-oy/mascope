from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from backend.db import db_path

# Database configuration
DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Check connection liveness before using a connection from the pool
    connect_args={
        "timeout": 15
    },  # Set a timeout of 15 seconds for establishing connections and waiting for table locks
)


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
