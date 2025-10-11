"""
Test configuration and fixtures for RCA Engine tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator
import os

# Set test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_at_least_32_characters_long"
os.environ["POSTGRES_PASSWORD"] = "test_password"
os.environ["DEBUG"] = "True"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """Provide a test database session."""
    from core.db.database import DatabaseManager
    
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    async with db_manager.get_session() as session:
        yield session
    
    await db_manager.close()


@pytest.fixture
def sample_llm_messages():
    """Provide sample LLM messages for testing."""
    from core.llm.providers.base import LLMMessage
    
    return [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content="Hello, how are you?"),
    ]
