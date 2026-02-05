"""Integration tests for institutions routes."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers


class TestListInstitutions:
    """Tests for GET /api/v1/institutions endpoint."""

    def test_list_institutions_as_admin(
        self, client: TestClient, admin_token, sample_institution
    ):
        """Test list institutions as admin returns data."""
        response = client.get(
            "/api/v1/institutions",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_institutions_as_rm(
        self, client: TestClient, rm_token, sample_institution
    ):
        """Test list institutions as RM returns data."""
        response = client.get(
            "/api/v1/institutions",
            headers=auth_headers(rm_token),
        )

        assert response.status_code == 200

    def test_list_institutions_as_client_forbidden(
        self, client: TestClient, client_token
    ):
        """Test list institutions as client returns 403."""
        response = client.get(
            "/api/v1/institutions",
            headers=auth_headers(client_token),
        )

        assert response.status_code == 403

    def test_list_institutions_pagination(
        self, client: TestClient, admin_token, sample_institution
    ):
        """Test list institutions with pagination parameters."""
        response = client.get(
            "/api/v1/institutions?page=1&per_page=10",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10

    def test_list_institutions_filter_by_type(
        self, client: TestClient, admin_token, sample_institution
    ):
        """Test list institutions filtered by type."""
        response = client.get(
            "/api/v1/institutions?institution_type=bank",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["institution_type"] == "bank"

    def test_list_institutions_filter_by_active(
        self, client: TestClient, admin_token, sample_institution
    ):
        """Test list institutions filtered by active status."""
        response = client.get(
            "/api/v1/institutions?is_active=true",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["is_active"] is True

    def test_list_institutions_search(
        self, client: TestClient, admin_token, sample_institution
    ):
        """Test list institutions with search parameter."""
        response = client.get(
            "/api/v1/institutions?search=Banco",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


class TestGetInstitution:
    """Tests for GET /api/v1/institutions/{id} endpoint."""

    def test_get_institution_success(
        self, client: TestClient, admin_token, sample_institution
    ):
        """Test get institution by ID returns data."""
        response = client.get(
            f"/api/v1/institutions/{sample_institution.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_institution.id
        assert data["name"] == "Banco Teste"

    def test_get_institution_not_found(
        self, client: TestClient, admin_token
    ):
        """Test get institution with non-existent ID returns 404."""
        response = client.get(
            "/api/v1/institutions/non-existent-id",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 404


class TestCreateInstitution:
    """Tests for POST /api/v1/institutions endpoint."""

    def test_create_institution_success(
        self, client: TestClient, admin_token
    ):
        """Test create institution with valid data."""
        response = client.post(
            "/api/v1/institutions",
            headers=auth_headers(admin_token),
            json={
                "name": "Nova Instituição",
                "code": "002",
                "institution_type": "broker",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Nova Instituição"
        assert data["code"] == "002"
        assert data["institution_type"] == "broker"
        assert data["is_active"] is True

    def test_create_institution_minimal_data(
        self, client: TestClient, admin_token
    ):
        """Test create institution with minimal required data."""
        response = client.post(
            "/api/v1/institutions",
            headers=auth_headers(admin_token),
            json={
                "name": "Instituição Mínima",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Instituição Mínima"
        assert data["institution_type"] == "bank"  # default

    def test_create_institution_missing_name(
        self, client: TestClient, admin_token
    ):
        """Test create institution without required name fails."""
        response = client.post(
            "/api/v1/institutions",
            headers=auth_headers(admin_token),
            json={
                "code": "003",
            },
        )

        assert response.status_code == 422


class TestUpdateInstitution:
    """Tests for PUT /api/v1/institutions/{id} endpoint."""

    def test_update_institution_success(
        self, client: TestClient, admin_token, sample_institution
    ):
        """Test update institution with valid data."""
        response = client.put(
            f"/api/v1/institutions/{sample_institution.id}",
            headers=auth_headers(admin_token),
            json={
                "name": "Banco Atualizado",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Banco Atualizado"

    def test_update_institution_not_found(
        self, client: TestClient, admin_token
    ):
        """Test update non-existent institution returns 404."""
        response = client.put(
            "/api/v1/institutions/non-existent-id",
            headers=auth_headers(admin_token),
            json={"name": "Updated"},
        )

        assert response.status_code == 404

    def test_update_institution_deactivate(
        self, client: TestClient, admin_token, sample_institution
    ):
        """Test deactivate institution via update."""
        response = client.put(
            f"/api/v1/institutions/{sample_institution.id}",
            headers=auth_headers(admin_token),
            json={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False


class TestDeleteInstitution:
    """Tests for DELETE /api/v1/institutions/{id} endpoint."""

    def test_delete_institution_success(
        self, client: TestClient, admin_token, sample_institution
    ):
        """Test delete institution (soft delete)."""
        response = client.delete(
            f"/api/v1/institutions/{sample_institution.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 204

        # Verify it's deactivated (soft delete)
        get_response = client.get(
            f"/api/v1/institutions/{sample_institution.id}",
            headers=auth_headers(admin_token),
        )
        assert get_response.status_code == 200
        assert get_response.json()["is_active"] is False

    def test_delete_institution_not_found(
        self, client: TestClient, admin_token
    ):
        """Test delete non-existent institution returns 404."""
        response = client.delete(
            "/api/v1/institutions/non-existent-id",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 404
