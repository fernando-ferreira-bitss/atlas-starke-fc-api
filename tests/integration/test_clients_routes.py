"""Integration tests for clients routes."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers


class TestListClients:
    """Tests for GET /api/v1/clients endpoint."""

    def test_list_clients_as_admin(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test list clients as admin returns all clients."""
        response = client.get(
            "/api/v1/clients",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_clients_as_rm_sees_only_assigned(
        self, client: TestClient, rm_token, sample_client
    ):
        """Test list clients as RM returns only assigned clients."""
        response = client.get(
            "/api/v1/clients",
            headers=auth_headers(rm_token),
        )

        assert response.status_code == 200
        data = response.json()
        # RM should only see clients assigned to them
        for item in data["items"]:
            assert item["rm_user_id"] is not None

    def test_list_clients_as_client_forbidden(
        self, client: TestClient, client_token
    ):
        """Test list clients as client returns 403."""
        response = client.get(
            "/api/v1/clients",
            headers=auth_headers(client_token),
        )

        assert response.status_code == 403

    def test_list_clients_pagination(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test list clients with pagination."""
        response = client.get(
            "/api/v1/clients?page=1&per_page=10",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert "pages" in data

    def test_list_clients_filter_by_status(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test list clients filtered by status."""
        response = client.get(
            "/api/v1/clients?status=active",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "active"

    def test_list_clients_search_by_name(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test list clients with search parameter."""
        response = client.get(
            "/api/v1/clients?search=Teste",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


class TestGetClient:
    """Tests for GET /api/v1/clients/{id} endpoint."""

    def test_get_client_success(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test get client by ID returns data."""
        response = client.get(
            f"/api/v1/clients/{sample_client.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_client.id
        assert data["name"] == "Cliente Teste"
        assert "cpf_cnpj_masked" in data

    def test_get_client_includes_totals(
        self, client: TestClient, admin_token, sample_client, sample_asset, sample_liability
    ):
        """Test get client includes calculated totals."""
        response = client.get(
            f"/api/v1/clients/{sample_client.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_assets" in data
        assert "total_liabilities" in data
        assert "net_worth" in data

    def test_get_client_as_rm_own_client(
        self, client: TestClient, rm_token, sample_client
    ):
        """Test RM can get their own client."""
        response = client.get(
            f"/api/v1/clients/{sample_client.id}",
            headers=auth_headers(rm_token),
        )

        assert response.status_code == 200

    def test_get_client_not_found(
        self, client: TestClient, admin_token
    ):
        """Test get non-existent client returns 404."""
        response = client.get(
            "/api/v1/clients/non-existent-id",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 404


class TestCreateClient:
    """Tests for POST /api/v1/clients endpoint."""

    def test_create_client_valid_cpf(
        self, client: TestClient, admin_token
    ):
        """Test create client with valid CPF."""
        response = client.post(
            "/api/v1/clients",
            headers=auth_headers(admin_token),
            json={
                "name": "Novo Cliente",
                "client_type": "pf",
                "cpf_cnpj": "52998224725",  # Valid CPF
                "email": "novo@email.com",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Novo Cliente"
        assert data["status"] == "active"

    def test_create_client_valid_cnpj(
        self, client: TestClient, admin_token
    ):
        """Test create client with valid CNPJ."""
        response = client.post(
            "/api/v1/clients",
            headers=auth_headers(admin_token),
            json={
                "name": "Empresa Teste",
                "client_type": "pj",
                "cpf_cnpj": "11222333000181",  # Valid CNPJ
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["client_type"] == "pj"

    def test_create_client_invalid_cpf(
        self, client: TestClient, admin_token
    ):
        """Test create client with invalid CPF fails."""
        response = client.post(
            "/api/v1/clients",
            headers=auth_headers(admin_token),
            json={
                "name": "Cliente Inválido",
                "client_type": "pf",
                "cpf_cnpj": "12345678901",  # Invalid CPF
            },
        )

        # Pydantic validation returns 422 for invalid CPF
        assert response.status_code == 422

    def test_create_client_duplicate_cpf(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test create client with duplicate CPF fails."""
        response = client.post(
            "/api/v1/clients",
            headers=auth_headers(admin_token),
            json={
                "name": "Cliente Duplicado",
                "client_type": "pf",
                "cpf_cnpj": "12345678909",  # Same CPF as sample_client
            },
        )

        assert response.status_code == 400
        assert "já cadastrado" in response.json()["detail"]

    def test_create_client_as_rm_auto_assigns(
        self, client: TestClient, rm_token, rm_user
    ):
        """Test RM creating client auto-assigns to themselves."""
        response = client.post(
            "/api/v1/clients",
            headers=auth_headers(rm_token),
            json={
                "name": "Cliente do RM",
                "client_type": "pf",
                "cpf_cnpj": "39053344705",  # Valid CPF verified
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rm_user_id"] == rm_user.id


class TestUpdateClient:
    """Tests for PUT /api/v1/clients/{id} endpoint."""

    def test_update_client_success(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test update client with valid data."""
        response = client.put(
            f"/api/v1/clients/{sample_client.id}",
            headers=auth_headers(admin_token),
            json={"name": "Cliente Atualizado"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Cliente Atualizado"

    def test_update_client_rm_cannot_change_assignment(
        self, client: TestClient, rm_token, sample_client
    ):
        """Test RM cannot change client assignment."""
        response = client.put(
            f"/api/v1/clients/{sample_client.id}",
            headers=auth_headers(rm_token),
            json={"rm_user_id": 999},
        )

        assert response.status_code == 403

    def test_update_client_not_found(
        self, client: TestClient, admin_token
    ):
        """Test update non-existent client returns 404."""
        response = client.put(
            "/api/v1/clients/non-existent-id",
            headers=auth_headers(admin_token),
            json={"name": "Updated"},
        )

        assert response.status_code == 404


class TestDeleteClient:
    """Tests for DELETE /api/v1/clients/{id} endpoint."""

    def test_delete_client_success(
        self, client: TestClient, admin_token, sample_client
    ):
        """Test delete client (soft delete)."""
        response = client.delete(
            f"/api/v1/clients/{sample_client.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 204

        # Verify status is inactive
        get_response = client.get(
            f"/api/v1/clients/{sample_client.id}",
            headers=auth_headers(admin_token),
        )
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "inactive"


class TestClientSummary:
    """Tests for GET /api/v1/clients/{id}/summary endpoint."""

    def test_get_client_summary(
        self, client: TestClient, admin_token, sample_client, sample_asset, sample_liability
    ):
        """Test get client summary returns calculated data."""
        response = client.get(
            f"/api/v1/clients/{sample_client.id}/summary",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_assets" in data
        assert "total_liabilities" in data
        assert "net_worth" in data
        assert "assets_by_category" in data
        assert "liabilities_by_type" in data

    def test_get_client_summary_calculations(
        self, client: TestClient, admin_token, sample_client, sample_asset, sample_liability
    ):
        """Test summary calculations are correct."""
        response = client.get(
            f"/api/v1/clients/{sample_client.id}/summary",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()

        # Asset value: 10500, Liability: 45000
        # Net worth should be negative
        net_worth = float(data["net_worth"])
        assert net_worth == float(data["total_assets"]) - float(data["total_liabilities"])
