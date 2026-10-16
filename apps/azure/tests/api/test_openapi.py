"""Testes do schema OpenAPI para as rotas do app azure."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class TestAzureOpenApiSchema:
    """Testes cobrindo a geração do schema com as rotas do app azure."""

    def test_schema_inclui_a_operacao_de_backlog(
        self, api_client: APIClient, settings
    ) -> None:
        """O schema gera com sucesso e inclui o operationId do app."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(
            reverse("api-schema"), HTTP_X_API_KEY="chave-correta"
        )

        assert response.status_code == status.HTTP_200_OK
        conteudo = response.content
        assert b"azure_backlog" in conteudo
        assert b"azure_backlog_post" in conteudo
        assert b"azure_backlog_diagnostics" in conteudo
        assert b"azure_projects" in conteudo
