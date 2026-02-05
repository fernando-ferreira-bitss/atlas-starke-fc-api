"""Integration tests for positions endpoints.

These tests call the API running locally on port 8000.
Make sure the API is running before executing these tests.
"""

import requests
import pytest
from io import BytesIO

# API base URL
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

# Test credentials
TEST_EMAIL = "admin@starke.com"
TEST_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token from the running API."""
    response = requests.post(
        f"{API_URL}/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestHealthCheck:
    """Basic API connectivity tests."""

    def test_api_is_running(self):
        """Test that the API is running."""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            # Some APIs don't have /health, try /docs
            if response.status_code == 404:
                response = requests.get(f"{BASE_URL}/docs", timeout=5)
            assert response.status_code in [200, 307]
        except requests.exceptions.ConnectionError:
            pytest.fail("API is not running on localhost:8000")


class TestPositionItems:
    """Integration tests for GET /api/v1/positions/items endpoint."""

    def test_list_items_success(self, auth_headers):
        """Test listing position items successfully."""
        response = requests.get(
            f"{API_URL}/positions/items",
            headers=auth_headers,
            params={"page": 1, "per_page": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data
        assert data["page"] == 1
        assert data["per_page"] == 10

    def test_list_items_with_year_filter(self, auth_headers):
        """Test listing items with year filter."""
        response = requests.get(
            f"{API_URL}/positions/items",
            headers=auth_headers,
            params={"page": 1, "per_page": 10, "year": 2025},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_items_with_month_filter(self, auth_headers):
        """Test listing items with month filter."""
        response = requests.get(
            f"{API_URL}/positions/items",
            headers=auth_headers,
            params={"page": 1, "per_page": 10, "year": 2025, "month": 12},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_items_with_search(self, auth_headers):
        """Test listing items with search query."""
        response = requests.get(
            f"{API_URL}/positions/items",
            headers=auth_headers,
            params={"page": 1, "per_page": 10, "search": "test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_items_invalid_month(self, auth_headers):
        """Test listing items with invalid month."""
        response = requests.get(
            f"{API_URL}/positions/items",
            headers=auth_headers,
            params={"page": 1, "per_page": 10, "month": 13},
        )
        assert response.status_code == 422  # Validation error

    def test_list_items_without_auth(self):
        """Test that endpoint requires authentication."""
        response = requests.get(
            f"{API_URL}/positions/items",
            params={"page": 1, "per_page": 10},
        )
        assert response.status_code == 401


class TestPositionValidate:
    """Integration tests for GET /api/v1/positions/validate endpoint."""

    def test_validate_success(self, auth_headers):
        """Test validating positions for a period."""
        response = requests.get(
            f"{API_URL}/positions/validate",
            headers=auth_headers,
            params={"year": 2025, "month": 12},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_items" in data
        assert "valid_count" in data
        assert "invalid_count" in data
        assert "errors" in data

    def test_validate_missing_year(self, auth_headers):
        """Test validation requires year parameter."""
        response = requests.get(
            f"{API_URL}/positions/validate",
            headers=auth_headers,
            params={"month": 12},
        )
        assert response.status_code == 422

    def test_validate_missing_month(self, auth_headers):
        """Test validation requires month parameter."""
        response = requests.get(
            f"{API_URL}/positions/validate",
            headers=auth_headers,
            params={"year": 2025},
        )
        assert response.status_code == 422

    def test_validate_invalid_month(self, auth_headers):
        """Test validation with invalid month value."""
        response = requests.get(
            f"{API_URL}/positions/validate",
            headers=auth_headers,
            params={"year": 2025, "month": 13},
        )
        assert response.status_code == 422

    def test_validate_without_auth(self):
        """Test that endpoint requires authentication."""
        response = requests.get(
            f"{API_URL}/positions/validate",
            params={"year": 2025, "month": 12},
        )
        assert response.status_code == 401


class TestPositionImportHistory:
    """Integration tests for GET /api/v1/positions/import-history endpoint."""

    def test_list_history_success(self, auth_headers):
        """Test listing import history."""
        response = requests.get(
            f"{API_URL}/positions/import-history",
            headers=auth_headers,
            params={"page": 1, "per_page": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data

    def test_list_history_pagination(self, auth_headers):
        """Test pagination parameters."""
        response = requests.get(
            f"{API_URL}/positions/import-history",
            headers=auth_headers,
            params={"page": 2, "per_page": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["per_page"] == 5

    def test_list_history_without_auth(self):
        """Test that endpoint requires authentication."""
        response = requests.get(
            f"{API_URL}/positions/import-history",
            params={"page": 1, "per_page": 10},
        )
        assert response.status_code == 401


class TestPositionImport:
    """Integration tests for POST /api/v1/positions/import endpoint."""

    def test_import_requires_file(self, auth_headers):
        """Test that file is required for import."""
        response = requests.post(
            f"{API_URL}/positions/import",
            headers=auth_headers,
            data={"reference_date": "2025-12-01"},
        )
        assert response.status_code == 422

    def test_import_requires_reference_date(self, auth_headers):
        """Test that reference_date is required."""
        csv_content = b"client_id,asset_id,value\n"
        response = requests.post(
            f"{API_URL}/positions/import",
            headers=auth_headers,
            files={"file": ("test.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 422

    def test_import_invalid_file_type(self, auth_headers):
        """Test import rejects invalid file types."""
        response = requests.post(
            f"{API_URL}/positions/import",
            headers=auth_headers,
            files={"file": ("test.txt", b"content", "text/plain")},
            data={"reference_date": "2025-12-01"},
        )
        assert response.status_code == 400
        assert "suportado" in response.json()["detail"].lower()

    def test_import_empty_csv(self, auth_headers):
        """Test import with empty CSV (headers only)."""
        csv_content = b"client_id,asset_id,value\n"
        response = requests.post(
            f"{API_URL}/positions/import",
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

    def test_import_csv_with_invalid_data(self, auth_headers):
        """Test import with invalid data in CSV."""
        csv_content = b"client_id,asset_id,value\ninvalid-uuid,invalid-uuid,100.00\n"
        response = requests.post(
            f"{API_URL}/positions/import",
            headers=auth_headers,
            files={"file": ("positions.csv", csv_content, "text/csv")},
            data={"reference_date": "2025-12-01"},
        )
        # Import may return 200 with errors or 500 if validation fails hard
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "errors" in data

    def test_import_invalid_date_format(self, auth_headers):
        """Test import with invalid date format."""
        csv_content = b"client_id,asset_id,value\n"
        response = requests.post(
            f"{API_URL}/positions/import",
            headers=auth_headers,
            files={"file": ("positions.csv", csv_content, "text/csv")},
            data={"reference_date": "01-12-2025"},  # Wrong format
        )
        assert response.status_code == 400
        assert "inv" in response.json()["detail"].lower()

    def test_import_without_auth(self):
        """Test that endpoint requires authentication."""
        csv_content = b"client_id,asset_id,value\n"
        response = requests.post(
            f"{API_URL}/positions/import",
            files={"file": ("positions.csv", csv_content, "text/csv")},
            data={"reference_date": "2025-12-01"},
        )
        assert response.status_code == 401


class TestPositionsMainEndpoint:
    """Integration tests for the main positions endpoint."""

    def test_list_positions_success(self, auth_headers):
        """Test listing positions grouped by client."""
        response = requests.get(
            f"{API_URL}/positions",
            headers=auth_headers,
            params={"page": 1, "per_page": 10, "year": 2025, "month": 12},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_positions_without_auth(self):
        """Test that positions endpoint requires authentication."""
        response = requests.get(
            f"{API_URL}/positions",
            params={"page": 1, "per_page": 10},
        )
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
