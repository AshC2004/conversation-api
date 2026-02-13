"""Shared test fixtures."""

import uuid

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def test_email():
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture(scope="module")
def test_password():
    return "SecureTestPass123"


@pytest.fixture(scope="module")
def auth_tokens(client, test_email, test_password):
    """Register a user and return tokens."""
    resp = client.post("/api/v1/auth/register", json={"email": test_email, "password": test_password})
    assert resp.status_code == 201
    return resp.json()["data"]


@pytest.fixture(scope="module")
def auth_header(auth_tokens):
    return {"Authorization": f"Bearer {auth_tokens['access_token']}"}
