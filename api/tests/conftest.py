"""
Pytest configuration and global fixtures.
"""

import pytest

from api.database import engine


@pytest.fixture(autouse=True)
async def dispose_db_engine():
    """
    Automatically dispose SQLAlchemy engine pool after every test.
    Prevents 'Event loop is closed' errors when pytest-asyncio creates
    new event loops per test function.
    """
    yield
    await engine.dispose()
