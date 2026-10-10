import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
