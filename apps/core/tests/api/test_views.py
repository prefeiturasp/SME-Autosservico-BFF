"""Testes do endpoint de health check."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class TestHealthCheckView:
    """Testes cobrindo GET /api/v1/health/."""

    def test_health_check_returns_ok(self, api_client: APIClient) -> None:
        """O endpoint responde com HTTP 200 e payload status=ok."""
        response = api_client.get(reverse("core:health"))

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}

    def test_health_check_does_not_require_authentication(
        self, api_client: APIClient
    ) -> None:
        """O endpoint é acessível sem chave de API ou autenticação."""
        response = api_client.get(reverse("core:health"))

        assert response.status_code != status.HTTP_401_UNAUTHORIZED
