import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

from app.main import app  # Your FastAPI application
from app.db import Base, get_db, settings # Import settings to potentially override DATABASE_URL for tests
from app.config import Settings

# Determine DATABASE_URL for tests - prioritize TEST_DATABASE_URL env var
# Fallback to regular DATABASE_URL if not set, but warn user or use a dedicated test DB
import os
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", settings.DATABASE_URL) 
# It's highly recommended to use a separate test database.
# If TEST_DATABASE_URL is the same as settings.DATABASE_URL, ensure it's safe to drop/create tables.

# Create a new async engine for the test database
test_engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for session scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Create tables at the start of the test session and drop them at the end."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a database session for a test function."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback() # Rollback any changes after each test to keep tests isolated

@pytest_asyncio.fixture(scope="function")
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provides an HTTP client for making requests to the FastAPI app, with overridden DB."""
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://127.0.0.1:8000") as client:
        yield client
    app.dependency_overrides.clear() 