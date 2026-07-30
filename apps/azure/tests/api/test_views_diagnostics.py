"""Testes da view de diagnóstico do backlog do Azure DevOps."""

from typing import Any
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.azure import cache as azure_cache

_CHAVE = "chave-correta"
_ORGANIZACAO = "SME-Spassu"
_PROJETO = "SME - Sustentação"
_DELAY = "apps.azure.tasks.atualizar_diagnostico.delay"


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


@pytest.fixture
def _configurar(settings) -> None:
    """Configura API Key e organização padrão para os testes da view."""
    settings.API_KEY = _CHAVE
    settings.AZURE_DEVOPS_ORGANIZATION = _ORGANIZACAO


def _get(api_client: APIClient, **params: Any) -> Any:
    """Faz um GET autenticado na view de diagnóstico.

    Args:
        api_client: Cliente de teste do DRF.
        **params: Query params da requisição.

    Returns:
        A resposta HTTP.
    """
    return api_client.get(
        reverse("azure:backlog-diagnostics"), params, HTTP_X_API_KEY=_CHAVE
    )


@pytest.mark.usefixtures("_configurar")
class TestBacklogDiagnosticsView:
    """Testes cobrindo GET /api/v1/azure/backlog/diagnostics/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(reverse("azure:backlog-diagnostics"))

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_project_name_obrigatorio(self, api_client: APIClient) -> None:
        """Sem `project_name`, retorna 400."""
        response = _get(api_client)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "project_name é obrigatório"}

    def test_cache_miss_dispara_task_e_devolve_vazio(
        self, api_client: APIClient
    ) -> None:
        """Em cache miss, dispara a task e devolve o diagnóstico vazio."""
        with patch(_DELAY) as mock_delay:
            response = _get(api_client, project_name=_PROJETO)

        mock_delay.assert_called_once_with(_ORGANIZACAO, _PROJETO)
        assert response.json() == {
            "project_name": _PROJETO,
            "total_items": 0,
            "work_item_type_counts": {},
            "sample_items": [],
        }

    def test_cache_hit_nao_dispara_task(self, api_client: APIClient) -> None:
        """Em cache hit, devolve o valor cacheado e não dispara task."""
        payload = {
            "project_name": _PROJETO,
            "total_items": 2,
            "work_item_type_counts": {"BugFix": 1, "Feature": 1},
            "sample_items": [
                {
                    "id": 1,
                    "title": "[SGP] Erro",
                    "type": "BugFix",
                    "state": "New",
                }
            ],
        }
        cache.set(
            azure_cache.chave_diagnostico(_ORGANIZACAO, _PROJETO), payload
        )

        with patch(_DELAY) as mock_delay:
            response = _get(api_client, project_name=_PROJETO)

        mock_delay.assert_not_called()
        assert response.json() == payload

    def test_organizacao_do_request_prevalece(
        self, api_client: APIClient
    ) -> None:
        """A organização do query param sobrepõe a do ambiente."""
        with patch(_DELAY) as mock_delay:
            _get(api_client, project_name=_PROJETO, organization="Outra-Org")

        mock_delay.assert_called_once_with("Outra-Org", _PROJETO)

    def test_organizacao_nao_resolvida(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem organização no request nem no ambiente, retorna 400."""
        settings.AZURE_DEVOPS_ORGANIZATION = ""

        response = _get(api_client, project_name=_PROJETO)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
