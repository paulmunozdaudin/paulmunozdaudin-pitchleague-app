import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import issue_dev_token
from app.db.session import get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=True, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_headers(sub: str, email: str, name: str) -> dict:
    token = issue_dev_token(sub=sub, email=email, name=name)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def alice_headers():
    return auth_headers("alice-sub", "alice@example.com", "Alice")


@pytest.fixture()
def bob_headers():
    return auth_headers("bob-sub", "bob@example.com", "Bob")
