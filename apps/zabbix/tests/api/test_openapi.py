"""Testes do schema OpenAPI para as rotas do app zabbix."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class TestZabbixOpenApiSchema:
    """Testes cobrindo a geração do schema com as rotas do app zabbix."""

    def test_schema_inclui_as_operacoes_do_zabbix(
        self, api_client: APIClient, settings
    ) -> None:
        """O schema gera com sucesso e inclui os operationIds do app."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(
            reverse("api-schema"), HTTP_X_API_KEY="chave-correta"
        )

        assert response.status_code == status.HTTP_200_OK
        conteudo = response.content
        assert b"zabbix_status_preset" in conteudo
        assert b"zabbix_disponibilidade_sistemas" in conteudo
        assert b"zabbix_database_status" in conteudo
        assert b"zabbix_jenkins_job_summary" in conteudo
