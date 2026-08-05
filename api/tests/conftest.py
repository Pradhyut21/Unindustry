"""
Pytest configuration and global fixtures.
"""

import os

import pytest


@pytest.fixture()
async def db_setup():
    """
    Initialize DB tables and dispose the engine pool after the test.

    Use this fixture explicitly in tests that need a real database connection:

        async def test_something(self, db_setup):
            ...

    Pure-function tests should NOT use this fixture — they run without any DB.
    """
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        pytest.skip("DATABASE_URL not set — skipping DB-dependent test")

    from api.database import engine, init_db

    await init_db()
    yield
    await engine.dispose()
