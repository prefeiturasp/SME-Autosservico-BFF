"""Testes do schema OpenAPI para as rotas do app sigpae."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class TestSigpaeOpenApiSchema:
    """Testes cobrindo a geração do schema com as rotas do app sigpae."""

    def test_schema_inclui_a_operacao_do_sigpae(
        self, api_client: APIClient, settings
    ) -> None:
        """O schema gera com sucesso e inclui o operationId do app."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(
            reverse("api-schema"), HTTP_X_API_KEY="chave-correta"
        )

        assert response.status_code == status.HTTP_200_OK
        assert b"sigpae_metricas" in response.content
