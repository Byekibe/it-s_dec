"""
Health check endpoint tests.

Tests for:
- GET /health
- GET /health/db
"""

import pytest


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.integration
    def test_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.get_json()

        assert data.get("status") == "healthy" or data.get("status") == "ok"

    @pytest.mark.integration
    def test_health_check_no_auth_required(self, client):
        """Test that health check doesn't require authentication."""
        # Should work without any headers
        response = client.get("/health")

        assert response.status_code == 200

    @pytest.mark.integration
    def test_database_health_check(self, client):
        """Test database connectivity health check."""
        response = client.get("/health/db")

        assert response.status_code == 200
        data = response.get_json()

        assert data.get("status") in ["healthy", "ok"]
        # Database field is a string "connected" or "disconnected"
        if "database" in data:
            assert data["database"] == "connected"

    @pytest.mark.integration
    def test_database_health_no_auth_required(self, client):
        """Test that database health check doesn't require authentication."""
        response = client.get("/health/db")

        assert response.status_code == 200
