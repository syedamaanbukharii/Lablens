"""API integration tests."""
import uuid

import pytest
from fastapi.testclient import TestClient

from lablens.api.main import app
from tests.conftest import SAMPLE_LAB_TEXT


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _unique_email():
    return f"{uuid.uuid4().hex[:8]}@lab.com"


def test_health(client):
    assert client.get("/api/health").status_code == 200


def test_register_and_login(client):
    email = _unique_email()
    r = client.post("/api/auth/register", json={"email": email, "password": "password123", "full_name": "Test"})
    assert r.status_code == 201
    token = r.json()["access_token"]
    r2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["email"] == email


def test_duplicate_register(client):
    email = _unique_email()
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    r = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 409


def test_login(client):
    email = _unique_email()
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    r = client.post("/api/auth/login", data={"username": email, "password": "password123"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_bad_login(client):
    r = client.post("/api/auth/login", data={"username": "no@one.com", "password": "wrong"})
    assert r.status_code == 401


def test_upload_requires_auth(client):
    r = client.post("/api/reports/upload", files={"file": ("t.txt", b"data", "text/plain")})
    assert r.status_code == 401


def _get_token(client) -> str:
    email = _unique_email()
    r = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    return r.json()["access_token"]


def test_upload_and_analyze(client):
    token = _get_token(client)
    r = client.post("/api/reports/upload",
                    files={"file": ("report.txt", SAMPLE_LAB_TEXT.encode(), "text/plain")},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "processed"
    assert body["total_markers"] >= 12
    assert body["abnormal_count"] > 0
    glucose = next((m for m in body["markers"] if m["name"] == "fasting_blood_glucose"), None)
    assert glucose is not None
    assert glucose["status"] == "high"
    assert "elevated" in glucose["interpretation"].lower() or "prediabetes" in glucose["interpretation"].lower()


def test_list_reports(client):
    token = _get_token(client)
    client.post("/api/reports/upload",
                files={"file": ("r.txt", SAMPLE_LAB_TEXT.encode(), "text/plain")},
                headers={"Authorization": f"Bearer {token}"})
    r = client.get("/api/reports", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_dashboard(client):
    token = _get_token(client)
    client.post("/api/reports/upload",
                files={"file": ("r.txt", SAMPLE_LAB_TEXT.encode(), "text/plain")},
                headers={"Authorization": f"Bearer {token}"})
    r = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["total_reports"] >= 1
