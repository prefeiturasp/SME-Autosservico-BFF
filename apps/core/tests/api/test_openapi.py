"""Testes do schema OpenAPI e do Swagger UI."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class TestOpenApiSchema:
    """Testes cobrindo GET /api/v1/schema/ e GET /api/v1/docs/.

    Como este serviço não possui banco de dados/usuários, o schema e o
    Swagger UI são protegidos pela mesma API Key das demais rotas, em vez
    de login de superusuário.
    """

    def test_schema_requires_api_key(self, api_client: APIClient) -> None:
        """Sem a API Key, o schema retorna 401."""
        response = api_client.get(reverse("api-schema"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_schema_accessible_with_api_key(
        self, api_client: APIClient, settings
    ) -> None:
        """Com a API Key correta, o schema é gerado com sucesso."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(
            reverse("api-schema"), HTTP_X_API_KEY="chave-correta"
        )

        assert response.status_code == status.HTTP_200_OK

    def test_docs_requires_api_key(self, api_client: APIClient) -> None:
        """Sem a API Key, o Swagger UI retorna 401."""
        response = api_client.get(reverse("api-docs"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_docs_accessible_with_api_key(
        self, api_client: APIClient, settings
    ) -> None:
        """Com a API Key correta, o Swagger UI é acessível."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(
            reverse("api-docs"), HTTP_X_API_KEY="chave-correta"
        )

        assert response.status_code == status.HTTP_200_OK
