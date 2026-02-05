"""Integration tests for authentication routes."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers


class TestLogin:
    """Tests for POST /api/v1/auth/login endpoint."""

    def test_login_valid_credentials(self, client: TestClient, admin_user):
        """Test login with valid credentials returns token."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "Admin@123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_email_not_found(self, client: TestClient, admin_user):
        """Test login with non-existent email returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent@test.com", "password": "password"},
        )

        assert response.status_code == 401

    def test_login_wrong_password(self, client: TestClient, admin_user):
        """Test login with wrong password returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "WrongPassword"},
        )

        assert response.status_code == 401

    def test_login_inactive_user(self, client: TestClient, inactive_user):
        """Test login with inactive user returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "inactive@test.com", "password": "Inactive@123"},
        )

        assert response.status_code == 401


class TestMe:
    """Tests for GET /api/v1/auth/me endpoint."""

    def test_me_with_valid_token(self, client: TestClient, admin_user, admin_token):
        """Test /me with valid token returns user data."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers(admin_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["full_name"] == "Admin User"
        assert data["role"] == "admin"

    def test_me_without_token(self, client: TestClient):
        """Test /me without token returns 401."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_me_with_invalid_token(self, client: TestClient):
        """Test /me with invalid token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers("invalid_token"),
        )

        assert response.status_code == 401

    def test_me_returns_role(self, client: TestClient, rm_user, rm_token):
        """Test /me returns correct role for RM user."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers(rm_token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "rm"


class TestChangePassword:
    """Tests for POST /api/v1/auth/change-password endpoint."""

    def test_change_password_success(self, client: TestClient, admin_user, admin_token):
        """Test change password with correct current password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers(admin_token),
            json={
                "current_password": "Admin@123",
                "new_password": "NewAdmin@123",
            },
        )

        # Endpoint returns 204 No Content on success
        assert response.status_code == 204

        # Verify can login with new password
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "NewAdmin@123"},
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_current(self, client: TestClient, admin_user, admin_token):
        """Test change password with wrong current password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers(admin_token),
            json={
                "current_password": "WrongPassword",
                "new_password": "NewAdmin@123",
            },
        )

        assert response.status_code == 400

    def test_change_password_without_auth(self, client: TestClient):
        """Test change password without authentication."""
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "Admin@123",
                "new_password": "NewAdmin@123",
            },
        )

        assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/v1/auth/logout endpoint."""

    def test_logout_success(self, client: TestClient, admin_user, admin_token):
        """Test logout with valid token."""
        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers(admin_token),
        )

        # Endpoint returns 204 No Content on success
        assert response.status_code == 204

    def test_logout_without_auth(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401


class TestRoleBasedAccess:
    """Tests for role-based access in auth endpoints."""

    def test_all_roles_can_access_me(
        self, client: TestClient,
        admin_user, admin_token,
        rm_user, rm_token,
        analyst_user, analyst_token,
        client_user, client_token,
    ):
        """Test that all roles can access /me endpoint."""
        tokens = [admin_token, rm_token, analyst_token, client_token]

        for token in tokens:
            response = client.get(
                "/api/v1/auth/me",
                headers=auth_headers(token),
            )
            assert response.status_code == 200

    def test_all_roles_can_change_password(
        self, client: TestClient,
        admin_user, admin_token,
    ):
        """Test that users can change their own password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers(admin_token),
            json={
                "current_password": "Admin@123",
                "new_password": "Changed@123",
            },
        )
        # Endpoint returns 204 No Content on success
        assert response.status_code == 204
