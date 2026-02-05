"""Integration tests for users routes."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers


class TestListUsers:
    """Tests for GET /api/v1/users endpoint."""

    def test_list_users_as_admin(
        self, client: TestClient, admin_token, admin_user
    ):
        """Test list users as admin."""
        response = client.get(
            "/api/v1/users",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        # Endpoint returns a list of users, not paginated
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_users_as_rm_forbidden(
        self, client: TestClient, rm_token
    ):
        """Test list users as RM returns 403."""
        response = client.get(
            "/api/v1/users",
            headers=auth_headers(rm_token),
        )

        assert response.status_code == 403

    def test_list_users_as_analyst_forbidden(
        self, client: TestClient, analyst_token
    ):
        """Test list users as analyst returns 403."""
        response = client.get(
            "/api/v1/users",
            headers=auth_headers(analyst_token),
        )

        assert response.status_code == 403

    def test_list_users_filter_by_role(
        self, client: TestClient, admin_token, admin_user
    ):
        """Test list users filtered by role."""
        response = client.get(
            "/api/v1/users?role=admin",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        # Endpoint returns a list of users, not paginated
        assert isinstance(data, list)
        for item in data:
            assert item["role"] == "admin"


class TestGetUser:
    """Tests for GET /api/v1/users/{id} endpoint."""

    def test_get_user_as_admin(
        self, client: TestClient, admin_token, rm_user
    ):
        """Test get user by ID as admin."""
        response = client.get(
            f"/api/v1/users/{rm_user.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "rm@test.com"

    def test_get_user_not_found(
        self, client: TestClient, admin_token
    ):
        """Test get non-existent user returns 404."""
        response = client.get(
            "/api/v1/users/999999",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 404


class TestCreateUser:
    """Tests for POST /api/v1/users endpoint."""

    def test_create_user_as_admin(
        self, client: TestClient, admin_token
    ):
        """Test create user as admin."""
        response = client.post(
            "/api/v1/users",
            headers=auth_headers(admin_token),
            json={
                "email": "newuser@test.com",
                "password": "NewUser@123",
                "full_name": "New User",
                "role": "analyst",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "analyst"
        assert data["is_active"] is True

    def test_create_user_duplicate_email(
        self, client: TestClient, admin_token, admin_user
    ):
        """Test create user with duplicate email fails."""
        response = client.post(
            "/api/v1/users",
            headers=auth_headers(admin_token),
            json={
                "email": "admin@test.com",  # Existing email
                "password": "Password@123",
                "full_name": "Duplicate User",
                "role": "analyst",
            },
        )

        assert response.status_code == 400

    def test_create_user_as_rm_forbidden(
        self, client: TestClient, rm_token
    ):
        """Test create user as RM is forbidden."""
        response = client.post(
            "/api/v1/users",
            headers=auth_headers(rm_token),
            json={
                "email": "newuser@test.com",
                "password": "NewUser@123",
                "full_name": "New User",
                "role": "analyst",
            },
        )

        assert response.status_code == 403


class TestUpdateUser:
    """Tests for PUT /api/v1/users/{id} endpoint."""

    def test_update_user_as_admin(
        self, client: TestClient, admin_token, rm_user
    ):
        """Test update user as admin."""
        response = client.put(
            f"/api/v1/users/{rm_user.id}",
            headers=auth_headers(admin_token),
            json={"full_name": "Updated RM User"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated RM User"

    def test_update_user_change_role(
        self, client: TestClient, admin_token, analyst_user
    ):
        """Test update user role as admin."""
        response = client.put(
            f"/api/v1/users/{analyst_user.id}",
            headers=auth_headers(admin_token),
            json={"role": "rm"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "rm"

    def test_update_user_not_found(
        self, client: TestClient, admin_token
    ):
        """Test update non-existent user returns 404."""
        response = client.put(
            "/api/v1/users/999999",
            headers=auth_headers(admin_token),
            json={"full_name": "Updated"},
        )

        assert response.status_code == 404


class TestDeleteUser:
    """Tests for DELETE /api/v1/users/{id} endpoint."""

    def test_delete_user_as_admin(
        self, client: TestClient, admin_token, analyst_user
    ):
        """Test delete user as admin (soft delete)."""
        response = client.delete(
            f"/api/v1/users/{analyst_user.id}",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 204

    def test_delete_user_as_rm_forbidden(
        self, client: TestClient, rm_token, analyst_user
    ):
        """Test delete user as RM is forbidden."""
        response = client.delete(
            f"/api/v1/users/{analyst_user.id}",
            headers=auth_headers(rm_token),
        )

        assert response.status_code == 403

    def test_delete_user_not_found(
        self, client: TestClient, admin_token
    ):
        """Test delete non-existent user returns 404."""
        response = client.delete(
            "/api/v1/users/999999",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 404
