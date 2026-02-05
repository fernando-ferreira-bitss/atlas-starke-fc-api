"""Integration tests for accounts routes."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers


class TestListAccounts:
    """Tests for GET /api/v1/accounts endpoint."""

    def test_list_accounts_as_admin(
        self, client: TestClient, admin_token, sample_account
    ):
        """Test list accounts as admin."""
        response = client.get(
            "/api/v1/accounts",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_accounts_filter_by_client(
        self, client: TestClient, admin_token, sample_account, sample_client
    ):
        """Test list accounts filtered by client."""
        response = client.get(
            f"/api/v1/accounts?client_id={sample_client.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["client_id"] == sample_client.id


class TestGetAccountsByClient:
    """Tests for GET /api/v1/accounts/by-client/{client_id} endpoint."""

    def test_get_accounts_by_client(
        self, client: TestClient, admin_token, sample_account, sample_client
    ):
        """Test get all accounts for a client."""
        response = client.get(
            f"/api/v1/accounts/by-client/{sample_client.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_accounts_by_client_includes_institution(
        self, client: TestClient, admin_token, sample_account, sample_client
    ):
        """Test accounts include institution info."""
        response = client.get(
            f"/api/v1/accounts/by-client/{sample_client.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data[0]["institution"] is not None
        assert "name" in data[0]["institution"]


class TestCreateAccount:
    """Tests for POST /api/v1/accounts endpoint."""

    def test_create_account_success(
        self, client: TestClient, admin_token, sample_client, sample_institution
    ):
        """Test create account with valid data."""
        response = client.post(
            "/api/v1/accounts",
            headers=auth_headers(admin_token),
            json={
                "client_id": sample_client.id,
                "institution_id": sample_institution.id,
                "account_type": "savings",
                "account_number": "98765-4",
                "agency": "0002",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["account_type"] == "savings"
        assert data["is_active"] is True

    def test_create_account_invalid_institution(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test create account with invalid institution fails."""
        response = client.post(
            "/api/v1/accounts",
            headers=auth_headers(admin_token),
            json={
                "client_id": sample_client.id,
                "institution_id": "invalid-institution-id",
                "account_type": "checking",
            },
        )

        assert response.status_code == 400

    def test_create_account_without_institution(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test create account without institution (optional)."""
        response = client.post(
            "/api/v1/accounts",
            headers=auth_headers(admin_token),
            json={
                "client_id": sample_client.id,
                "account_type": "investment",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["institution_id"] is None


class TestUpdateAccount:
    """Tests for PUT /api/v1/accounts/{id} endpoint."""

    def test_update_account_success(
        self, client: TestClient, admin_token, sample_account
    ):
        """Test update account."""
        response = client.put(
            f"/api/v1/accounts/{sample_account.id}",
            headers=auth_headers(admin_token),
            json={"account_number": "11111-1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["account_number"] == "11111-1"


class TestDeleteAccount:
    """Tests for DELETE /api/v1/accounts/{id} endpoint."""

    def test_delete_account_success(
        self, client: TestClient, admin_token, sample_account
    ):
        """Test delete account (soft delete)."""
        response = client.delete(
            f"/api/v1/accounts/{sample_account.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 204

        # Verify it's deactivated
        get_response = client.get(
            f"/api/v1/accounts/{sample_account.id}",
            headers=auth_headers(admin_token),
        )
        assert get_response.json()["is_active"] is False
