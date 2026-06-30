"""Test fixtures — in-memory SQLite database and test client."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base_class import Base
from app.db.session import get_db
from app.main import app

# In-memory SQLite for fast, isolated tests
SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    """Provide a test client with the DB dependency overridden."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """Sign up a test user and return auth headers."""
    response = client.post(
        "/auth/signup",
        json={"email": "test@example.com", "password": "testpass123", "name": "Test User"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def second_auth_headers(client):
    """Sign up a second test user and return auth headers (for isolation tests)."""
    response = client.post(
        "/auth/signup",
        json={"email": "other@example.com", "password": "otherpass123", "name": "Other User"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
