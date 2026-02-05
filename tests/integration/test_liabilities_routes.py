"""Integration tests for liabilities routes."""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from tests.conftest import auth_headers


class TestListLiabilities:
    """Tests for GET /api/v1/liabilities endpoint."""

    def test_list_liabilities_as_admin(
        self, client: TestClient, admin_token, sample_liability
    ):
        """Test list liabilities as admin."""
        response = client.get(
            "/api/v1/liabilities",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_liabilities_ordered_by_balance(
        self, client: TestClient, admin_token, sample_liability
    ):
        """Test liabilities are ordered by current_balance DESC."""
        response = client.get(
            "/api/v1/liabilities",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        if len(items) > 1:
            for i in range(len(items) - 1):
                assert float(items[i]["current_balance"]) >= float(items[i + 1]["current_balance"])


class TestGetLiabilitiesByClient:
    """Tests for GET /api/v1/liabilities/by-client/{client_id} endpoint."""

    def test_get_liabilities_by_client(
        self, client: TestClient, admin_token, sample_liability, sample_client
    ):
        """Test get all liabilities for a client."""
        response = client.get(
            f"/api/v1/liabilities/by-client/{sample_client.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestGetLiabilitiesGrouped:
    """Tests for GET /api/v1/liabilities/by-client/{client_id}/grouped endpoint."""

    def test_get_liabilities_grouped_by_type(
        self, client: TestClient, admin_token, sample_liability, sample_client
    ):
        """Test get liabilities grouped by type."""
        response = client.get(
            f"/api/v1/liabilities/by-client/{sample_client.id}/grouped",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for group in data:
            assert "liability_type" in group
            assert "total_balance" in group
            assert "total_monthly_payment" in group
            assert "percentage" in group
            assert "liabilities" in group


class TestGetLiability:
    """Tests for GET /api/v1/liabilities/{id} endpoint."""

    def test_get_liability_includes_remaining_payments(
        self, client: TestClient, admin_token, sample_liability
    ):
        """Test get liability includes calculated remaining payments."""
        response = client.get(
            f"/api/v1/liabilities/{sample_liability.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        # current_balance=45000, monthly_payment=1500
        # remaining = 45000 / 1500 = 30
        assert data["remaining_payments"] is not None
        assert data["remaining_payments"] == 31  # int(45000/1500) + 1

    def test_get_liability_is_paid_off(
        self, client: TestClient, admin_token, sample_liability
    ):
        """Test liability is_paid_off property."""
        response = client.get(
            f"/api/v1/liabilities/{sample_liability.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        # current_balance=45000 > 0, so not paid off
        assert data["is_paid_off"] is False


class TestCreateLiability:
    """Tests for POST /api/v1/liabilities endpoint."""

    def test_create_liability_success(
        self, client: TestClient, admin_token, sample_client, sample_institution
    ):
        """Test create liability with valid data."""
        response = client.post(
            "/api/v1/liabilities",
            headers=auth_headers(admin_token),
            json={
                "client_id": sample_client.id,
                "institution_id": sample_institution.id,
                "liability_type": "mortgage",
                "description": "Financiamento Imobiliário",
                "original_amount": "500000.00",
                "current_balance": "450000.00",
                "monthly_payment": "5000.00",
                "interest_rate": "0.8",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["liability_type"] == "mortgage"
        assert data["is_active"] is True

    def test_create_liability_invalid_institution(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test create liability with invalid institution fails."""
        response = client.post(
            "/api/v1/liabilities",
            headers=auth_headers(admin_token),
            json={
                "client_id": sample_client.id,
                "institution_id": "invalid-institution-id",
                "liability_type": "personal_loan",
                "description": "Empréstimo",
                "original_amount": "10000.00",
                "current_balance": "8000.00",
            },
        )

        assert response.status_code == 400


class TestUpdateLiability:
    """Tests for PUT /api/v1/liabilities/{id} endpoint."""

    def test_update_liability_success(
        self, client: TestClient, admin_token, sample_liability
    ):
        """Test update liability."""
        response = client.put(
            f"/api/v1/liabilities/{sample_liability.id}",
            headers=auth_headers(admin_token),
            json={"current_balance": "40000.00"},
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["current_balance"]) == 40000.00


class TestDeleteLiability:
    """Tests for DELETE /api/v1/liabilities/{id} endpoint."""

    def test_delete_liability_success(
        self, client: TestClient, admin_token, sample_liability
    ):
        """Test delete liability (soft delete)."""
        response = client.delete(
            f"/api/v1/liabilities/{sample_liability.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 204

        # Verify it's deactivated
        get_response = client.get(
            f"/api/v1/liabilities/{sample_liability.id}",
            headers=auth_headers(admin_token),
        )
        assert get_response.json()["is_active"] is False
