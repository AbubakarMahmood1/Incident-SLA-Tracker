import httpx
import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.database import get_db
from app.main import app
from app.models import User

pytestmark = pytest.mark.postgres


def settings(database_url: str) -> Settings:
    return Settings(
        app_env="test",
        jwt_secret="integration-test-secret-that-is-long-enough",
        database_url=database_url,
        sla_high_response_minutes=30,
        sla_high_resolution_minutes=120,
    )


async def test_token_and_idempotent_create_use_sequential_request_transactions(
    db, users, postgres_url
) -> None:
    config = settings(postgres_url)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: config
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            token_response = await client.post(
                "/api/v1/auth/token",
                data={
                    "username": users["reporter"].username,
                    "password": "reporter password 123",
                },
            )
            assert token_response.status_code == 200
            token = token_response.json()["access_token"]

            headers = {
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "api-postgres-create-001",
            }
            payload = {
                "title": "Request transaction boundary",
                "description": "Authentication must finish before the command begins",
                "priority": "high",
            }
            first = await client.post("/api/v1/incidents", headers=headers, json=payload)
            repeated = await client.post("/api/v1/incidents", headers=headers, json=payload)

        assert first.status_code == 201
        assert repeated.status_code == 201
        assert first.json()["id"] == repeated.json()["id"]
    finally:
        app.dependency_overrides.clear()


async def test_api_authentication_and_authorization_matrix(db, users, postgres_url) -> None:
    config = settings(postgres_url)
    engine = create_async_engine(postgres_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_ids = {name: user.id for name, user in users.items()}
    usernames = {name: user.username for name, user in users.items()}

    async def override_db():
        async with factory() as session:
            yield session

    async def issue_token(client: httpx.AsyncClient, username: str, password: str) -> str:
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": username, "password": password},
        )
        assert response.status_code == 200
        return response.json()["access_token"]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: config
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            invalid_login = await client.post(
                "/api/v1/auth/token",
                data={"username": usernames["reporter"], "password": "wrong password"},
            )
            assert invalid_login.status_code == 401
            assert invalid_login.headers["www-authenticate"] == "Bearer"

            tokens = {
                name: await issue_token(client, usernames[name], f"{name} password 123")
                for name in users
                if name != "admin"
            }
            tokens["admin"] = await issue_token(
                client,
                usernames["admin"],
                "administrator password 123",
            )
            headers = {name: {"Authorization": f"Bearer {token}"} for name, token in tokens.items()}

            anonymous = await client.get("/api/v1/incidents")
            assert anonymous.status_code == 401

            missing_key = await client.post(
                "/api/v1/incidents",
                headers=headers["reporter"],
                json={
                    "title": "Missing receipt key",
                    "description": "Authenticated commands still require idempotency",
                    "priority": "high",
                },
            )
            assert missing_key.status_code == 422

            payload = {
                "title": "Authorization matrix",
                "description": "Every role boundary is exercised through the API",
                "priority": "high",
            }
            created = await client.post(
                "/api/v1/incidents",
                headers={
                    **headers["reporter"],
                    "Idempotency-Key": "api-authorization-create-001",
                },
                json=payload,
            )
            assert created.status_code == 201
            incident_id = created.json()["id"]

            conflicting = await client.post(
                "/api/v1/incidents",
                headers={
                    **headers["reporter"],
                    "Idempotency-Key": "api-authorization-create-001",
                },
                json={**payload, "title": "Conflicting replay"},
            )
            assert conflicting.status_code == 409
            assert conflicting.json()["error"]["code"] == "idempotency_conflict"

            invalid_key = await client.post(
                "/api/v1/incidents",
                headers={
                    **headers["reporter"],
                    "Idempotency-Key": "bad key",
                },
                json=payload,
            )
            assert invalid_key.status_code == 422
            assert invalid_key.json()["detail"]["code"] == "invalid_idempotency_key"

            outsider_detail = await client.get(
                f"/api/v1/incidents/{incident_id}",
                headers=headers["outsider"],
            )
            assert outsider_detail.status_code == 403
            outsider_list = await client.get("/api/v1/incidents", headers=headers["outsider"])
            assert outsider_list.status_code == 200
            assert outsider_list.json()["total"] == 0

            reporter_assignment = await client.post(
                f"/api/v1/incidents/{incident_id}/assign",
                headers={
                    **headers["reporter"],
                    "Idempotency-Key": "api-reporter-assign-001",
                },
                json={"assignee_id": str(user_ids["assignee"])},
            )
            assert reporter_assignment.status_code == 403

            assigned = await client.post(
                f"/api/v1/incidents/{incident_id}/assign",
                headers={
                    **headers["admin"],
                    "Idempotency-Key": "api-admin-assign-001",
                },
                json={"assignee_id": str(user_ids["assignee"])},
            )
            assert assigned.status_code == 200

            outsider_acknowledgement = await client.post(
                f"/api/v1/incidents/{incident_id}/acknowledge",
                headers={
                    **headers["outsider"],
                    "Idempotency-Key": "api-outsider-ack-001",
                },
            )
            assert outsider_acknowledgement.status_code == 403

            acknowledged = await client.post(
                f"/api/v1/incidents/{incident_id}/acknowledge",
                headers={
                    **headers["assignee"],
                    "Idempotency-Key": "api-assignee-ack-001",
                },
            )
            assert acknowledged.status_code == 200

            reporter_resolution = await client.post(
                f"/api/v1/incidents/{incident_id}/resolve",
                headers={
                    **headers["reporter"],
                    "Idempotency-Key": "api-reporter-resolve-001",
                },
            )
            assert reporter_resolution.status_code == 403

            resolved = await client.post(
                f"/api/v1/incidents/{incident_id}/resolve",
                headers={
                    **headers["assignee"],
                    "Idempotency-Key": "api-assignee-resolve-001",
                },
            )
            assert resolved.status_code == 200

            assignee_close = await client.post(
                f"/api/v1/incidents/{incident_id}/close",
                headers={
                    **headers["assignee"],
                    "Idempotency-Key": "api-assignee-close-001",
                },
            )
            assert assignee_close.status_code == 403

            closed = await client.post(
                f"/api/v1/incidents/{incident_id}/close",
                headers={
                    **headers["reporter"],
                    "Idempotency-Key": "api-reporter-close-001",
                },
            )
            assert closed.status_code == 200
            assert closed.json()["status"] == "closed"

            outsider_timeline = await client.get(
                f"/api/v1/incidents/{incident_id}/events",
                headers=headers["outsider"],
            )
            assert outsider_timeline.status_code == 403
            reporter_timeline = await client.get(
                f"/api/v1/incidents/{incident_id}/events",
                headers=headers["reporter"],
            )
            assert reporter_timeline.status_code == 200
            assert [event["event_type"] for event in reporter_timeline.json()["events"]] == [
                "incident.created",
                "incident.assigned",
                "incident.acknowledged",
                "incident.resolved",
                "incident.closed",
            ]

            async with db.begin():
                await db.execute(
                    update(User).where(User.id == user_ids["outsider"]).values(is_active=False)
                )
            deactivated = await client.get(
                "/api/v1/incidents",
                headers=headers["outsider"],
            )
            assert deactivated.status_code == 401
            assert deactivated.headers["www-authenticate"] == "Bearer"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
