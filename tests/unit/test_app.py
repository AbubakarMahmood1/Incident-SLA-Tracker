import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_liveness_does_not_require_database() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"
    assert response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_invalid_supplied_request_id_is_replaced() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live", headers={"X-Request-ID": "a" * 129})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"].isascii()


@pytest.mark.asyncio
async def test_valid_request_id_is_preserved() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live", headers={"X-Request-ID": "request-abc-123"})
    assert response.headers["X-Request-ID"] == "request-abc-123"


@pytest.mark.asyncio
async def test_readiness_fails_closed_without_database_driver_or_server() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


@pytest.mark.asyncio
@pytest.mark.parametrize("request_id", ["contains space", "tab\tvalue", "-starts-wrong"])
async def test_ambiguous_request_id_is_replaced(request_id: str) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live", headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != request_id
