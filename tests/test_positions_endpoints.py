"""Tests for positions endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from starke.api.main import app
from starke.api.dependencies import get_db
from starke.infrastructure.database.base import Base
from starke.infrastructure.database.models import User
from starke.domain.services.auth_service import AuthService


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    Base.metadata.create_all(bind=engine)

    # Create test user
    db = TestingSessionLocal()
    test_user = User(
        email="admin@starke.com",
        full_name="Admin User",
        hashed_password=AuthService.get_password_hash("admin123"),
        is_active=True,
        is_superuser=True,
        role="admin",
    )
    db.add(test_user)
    db.commit()
    db.close()

    with TestClient(app) as c:
        yield c

    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def auth_headers(client):
    """Get authentication headers."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@starke.com", "password": "admin123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestPositionItems:
    """Tests for GET /positions/items endpoint."""

    def test_list_items_empty(self, client, auth_headers):
        """Test listing items when empty."""
        response = client.get(
            "/api/v1/positions/items?page=1&per_page=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_items_with_filters(self, client, auth_headers):
        """Test listing items with filters."""
        response = client.get(
            "/api/v1/positions/items?page=1&per_page=10&year=2025&month=12",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_items_with_search(self, client, auth_headers):
        """Test listing items with search."""
        response = client.get(
            "/api/v1/positions/items?page=1&per_page=10&search=test",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestPositionValidate:
    """Tests for GET /positions/validate endpoint."""

    def test_validate_empty_period(self, client, auth_headers):
        """Test validation of empty period."""
        response = client.get(
            "/api/v1/positions/validate?year=2025&month=12",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_items" in data
        assert "valid_count" in data
        assert "invalid_count" in data
        assert "errors" in data
        assert data["total_items"] == 0
        assert data["valid_count"] == 0
        assert data["invalid_count"] == 0

    def test_validate_requires_year(self, client, auth_headers):
        """Test that year is required."""
        response = client.get(
            "/api/v1/positions/validate?month=12",
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_validate_requires_month(self, client, auth_headers):
        """Test that month is required."""
        response = client.get(
            "/api/v1/positions/validate?year=2025",
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error


class TestPositionImportHistory:
    """Tests for GET /positions/import-history endpoint."""

    def test_list_history_empty(self, client, auth_headers):
        """Test listing history when empty."""
        response = client.get(
            "/api/v1/positions/import-history?page=1&per_page=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_history_pagination(self, client, auth_headers):
        """Test pagination parameters."""
        response = client.get(
            "/api/v1/positions/import-history?page=2&per_page=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["per_page"] == 5


class TestPositionImport:
    """Tests for POST /positions/import endpoint."""

    def test_import_requires_file(self, client, auth_headers):
        """Test that file is required."""
        response = client.post(
            "/api/v1/positions/import",
            headers=auth_headers,
            data={"reference_date": "2025-12-01"},
        )
        assert response.status_code == 422  # Validation error

    def test_import_requires_reference_date(self, client, auth_headers):
        """Test that reference_date is required."""
        response = client.post(
            "/api/v1/positions/import",
            headers=auth_headers,
            files={"file": ("test.csv", b"client_id,asset_id,value", "text/csv")},
        )
        assert response.status_code == 422  # Validation error

    def test_import_invalid_file_type(self, client, auth_headers):
        """Test invalid file type."""
        response = client.post(
            "/api/v1/positions/import",
            headers=auth_headers,
            files={"file": ("test.txt", b"some content", "text/plain")},
            data={"reference_date": "2025-12-01"},
        )
        assert response.status_code == 400
        assert "não suportado" in response.json()["detail"]

    def test_import_csv_empty(self, client, auth_headers):
        """Test import with empty CSV."""
        csv_content = b"client_id,asset_id,value\n"
        response = client.post(
            "/api/v1/positions/import",
            headers=auth_headers,
            files={"file": ("positions.csv", csv_content, "text/csv")},
            data={"reference_date": "2025-12-01"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "imported_count" in data
        assert "errors" in data
        assert data["imported_count"] == 0

    def test_import_csv_with_invalid_data(self, client, auth_headers):
        """Test import with invalid data in CSV."""
        csv_content = b"client_id,asset_id,value\ninvalid-uuid,invalid-uuid,100.00\n"
        response = client.post(
            "/api/v1/positions/import",
            headers=auth_headers,
            files={"file": ("positions.csv", csv_content, "text/csv")},
            data={"reference_date": "2025-12-01"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0


class TestPositionEndpointsAuth:
    """Tests for authentication on position endpoints."""

    def test_items_requires_auth(self, client):
        """Test that /items requires authentication."""
        response = client.get("/api/v1/positions/items")
        assert response.status_code == 401

    def test_validate_requires_auth(self, client):
        """Test that /validate requires authentication."""
        response = client.get("/api/v1/positions/validate?year=2025&month=12")
        assert response.status_code == 401

    def test_import_history_requires_auth(self, client):
        """Test that /import-history requires authentication."""
        response = client.get("/api/v1/positions/import-history")
        assert response.status_code == 401

    def test_import_requires_auth(self, client):
        """Test that /import requires authentication."""
        response = client.post("/api/v1/positions/import")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
