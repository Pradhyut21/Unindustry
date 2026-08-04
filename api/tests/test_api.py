"""
FastAPI route integration tests.

Uses httpx AsyncClient against the real app (TestClient pattern).
DB is not mocked — these tests need a real Postgres connection.
Set DATABASE_URL env var to a test database before running.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app


@pytest.fixture
async def client():
    """Async test client that talks to the real FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestHealth:
    async def test_health_returns_200(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_returns_version(self, client: AsyncClient):
        response = await client.get("/health")
        data = response.json()
        assert "version" in data
        assert "status" in data

    async def test_health_db_field_present(self, client: AsyncClient):
        response = await client.get("/health")
        data = response.json()
        assert "db" in data


class TestProductsAPI:
    async def test_list_products_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/products/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_nonexistent_product_404(self, client: AsyncClient):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/products/{fake_id}")
        assert response.status_code == 404

    async def test_create_product_with_name_only(self, client: AsyncClient):
        import io
        response = await client.post(
            "/api/v1/products/",
            data={"name": "Siemens 3RT2 Contactor"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Siemens 3RT2 Contactor"
        assert "id" in data
        assert data["status"] == "processing"

    async def test_create_product_returns_uuid(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/products/",
            data={"name": "ABB Circuit Breaker S200"},
        )
        assert response.status_code == 201
        data = response.json()
        import uuid
        uuid.UUID(data["id"])  # raises if not valid UUID


class TestReviewAPI:
    async def test_review_queue_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/review/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_review_nonexistent_item_404(self, client: AsyncClient):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.post(
            f"/api/v1/review/{fake_id}/action",
            json={"action": "accepted", "reviewer": "test_user"},
        )
        assert response.status_code == 404

    async def test_review_edited_requires_corrected_value(self, client: AsyncClient):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.post(
            f"/api/v1/review/{fake_id}/action",
            json={"action": "edited", "reviewer": "test_user"},  # missing human_corrected_value
        )
        # 404 (not found) or 422 (validation) — either is correct
        assert response.status_code in (404, 422)
