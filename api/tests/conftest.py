"""
Pytest configuration and global fixtures.
"""

import pytest

from api.database import engine, init_db


@pytest.fixture(autouse=True)
async def setup_and_dispose_db():
    """
    1. Initialize DB tables before test runs.
    2. Automatically dispose SQLAlchemy engine pool after every test
       to prevent 'Event loop is closed' errors across test cases.
    """
    await init_db()
    yield
    await engine.dispose()
