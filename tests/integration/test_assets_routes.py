"""Integration tests for assets routes."""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from tests.conftest import auth_headers


class TestListAssets:
    """Tests for GET /api/v1/assets endpoint."""

    def test_list_assets_as_admin(
        self, client: TestClient, admin_token, sample_asset
    ):
        """Test list assets as admin."""
        response = client.get(
            "/api/v1/assets",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_assets_filter_by_category(
        self, client: TestClient, admin_token, sample_asset
    ):
        """Test list assets filtered by category."""
        response = client.get(
            "/api/v1/assets?category=renda_fixa",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["category"] == "renda_fixa"


class TestGetAssetsByClient:
    """Tests for GET /api/v1/assets/by-client/{client_id} endpoint."""

    def test_get_assets_by_client(
        self, client: TestClient, admin_token, sample_asset, sample_client
    ):
        """Test get all assets for a client."""
        response = client.get(
            f"/api/v1/assets/by-client/{sample_client.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestGetAssetsGrouped:
    """Tests for GET /api/v1/assets/by-client/{client_id}/grouped endpoint."""

    def test_get_assets_grouped_by_category(
        self, client: TestClient, admin_token, sample_asset, sample_client
    ):
        """Test get assets grouped by category."""
        response = client.get(
            f"/api/v1/assets/by-client/{sample_client.id}/grouped",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for group in data:
            assert "category" in group
            assert "total_value" in group
            assert "percentage" in group
            assert "assets" in group


class TestGetAsset:
    """Tests for GET /api/v1/assets/{id} endpoint."""

    def test_get_asset_includes_gain_loss(
        self, client: TestClient, admin_token, sample_asset
    ):
        """Test get asset includes calculated gain/loss."""
        response = client.get(
            f"/api/v1/assets/{sample_asset.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        # base_value=10000, current_value=10500
        # gain = 500, percent = 5%
        assert data["gain_loss"] is not None
        assert float(data["gain_loss"]) == 500.0
        assert data["gain_loss_percent"] is not None
        assert float(data["gain_loss_percent"]) == 5.0


class TestCreateAsset:
    """Tests for POST /api/v1/assets endpoint."""

    def test_create_asset_success(
        self, client: TestClient, admin_token, sample_client, sample_account
    ):
        """Test create asset with valid data."""
        response = client.post(
            "/api/v1/assets",
            headers=auth_headers(admin_token),
            json={
                "client_id": sample_client.id,
                "account_id": sample_account.id,
                "category": "renda_variavel",
                "subcategory": "acoes",
                "name": "PETR4",
                "ticker": "PETR4",
                "base_value": "1000.00",
                "current_value": "1200.00",
                "quantity": "10",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "PETR4"
        assert data["category"] == "renda_variavel"

    def test_create_asset_invalid_account(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test create asset with invalid account fails."""
        response = client.post(
            "/api/v1/assets",
            headers=auth_headers(admin_token),
            json={
                "client_id": sample_client.id,
                "account_id": "invalid-account-id",
                "category": "renda_fixa",
                "name": "CDB Inválido",
            },
        )

        assert response.status_code == 400

    def test_create_asset_without_account(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test create asset without account (optional)."""
        response = client.post(
            "/api/v1/assets",
            headers=auth_headers(admin_token),
            json={
                "client_id": sample_client.id,
                "category": "imoveis",
                "name": "Apartamento Centro",
                "current_value": "500000.00",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["account_id"] is None


class TestUpdateAsset:
    """Tests for PUT /api/v1/assets/{id} endpoint."""

    def test_update_asset_success(
        self, client: TestClient, admin_token, sample_asset
    ):
        """Test update asset."""
        response = client.put(
            f"/api/v1/assets/{sample_asset.id}",
            headers=auth_headers(admin_token),
            json={"current_value": "12000.00"},
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["current_value"]) == 12000.00


class TestDeleteAsset:
    """Tests for DELETE /api/v1/assets/{id} endpoint."""

    def test_delete_asset_success(
        self, client: TestClient, admin_token, sample_asset
    ):
        """Test delete asset (soft delete)."""
        response = client.delete(
            f"/api/v1/assets/{sample_asset.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 204

        # Verify it's deactivated
        get_response = client.get(
            f"/api/v1/assets/{sample_asset.id}",
            headers=auth_headers(admin_token),
        )
        assert get_response.json()["is_active"] is False
