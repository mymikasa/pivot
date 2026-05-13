from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from src.core.config import settings
from src.core.database import Base, get_db
from src.main import app
from tests.conftest import TestingSessionLocal, engine


def auth_headers() -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": "1",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_and_get_parse_task():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.post(
        "/api/v1/parse/tasks",
        json={
            "kb_id": 7,
            "document_id": 42,
            "object_key": "7/demo.txt",
            "content_type": "text/plain",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"

    detail = client.get(
        f"/api/v1/parse/tasks/{data['task_id']}",
        headers=auth_headers(),
    )
    assert detail.status_code == 200
    assert detail.json()["task_id"] == data["task_id"]

    app.dependency_overrides.clear()
