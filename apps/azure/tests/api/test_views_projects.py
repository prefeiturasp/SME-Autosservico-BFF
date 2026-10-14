"""Testes da view de listagem de projetos do Azure DevOps."""

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
_DELAY = "apps.azure.tasks.atualizar_projetos.delay"


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
    """Faz um GET autenticado na view de projetos.

    Args:
        api_client: Cliente de teste do DRF.
        **params: Query params da requisição.

    Returns:
        A resposta HTTP.
    """
    return api_client.get(
        reverse("azure:projects"), params, HTTP_X_API_KEY=_CHAVE
    )


@pytest.mark.usefixtures("_configurar")
class TestProjectsView:
    """Testes cobrindo GET /api/v1/azure/projects/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(reverse("azure:projects"))

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_top_fora_do_intervalo(self, api_client: APIClient) -> None:
        """`top` acima de 500 retorna 400."""
        response = _get(api_client, top="501")

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "top" in response.json()["error"]

    def test_top_nao_numerico(self, api_client: APIClient) -> None:
        """`top` não numérico retorna 400 em vez de 500."""
        response = _get(api_client, top="muitos")

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_skip_negativo(self, api_client: APIClient) -> None:
        """`skip` negativo retorna 400."""
        response = _get(api_client, skip="-1")

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "skip" in response.json()["error"]

    def test_cache_miss_dispara_task_com_os_padroes(
        self, api_client: APIClient
    ) -> None:
        """Sem paginação explícita, usa top=100 e skip=0."""
        with patch(_DELAY) as mock_delay:
            response = _get(api_client)

        mock_delay.assert_called_once_with(_ORGANIZACAO, 100, 0, None)
        assert response.json() == {
            "count": 0,
            "total_count": None,
            "projects": [],
            "continuation_token": None,
            "has_more": False,
        }

    def test_repassa_a_paginacao_para_a_task(
        self, api_client: APIClient
    ) -> None:
        """top, skip e continuation_token chegam na task."""
        with patch(_DELAY) as mock_delay:
            _get(
                api_client,
                top="50",
                skip="10",
                continuation_token="tk",  # noqa: S106
            )

        mock_delay.assert_called_once_with(_ORGANIZACAO, 50, 10, "tk")

    def test_cache_hit_nao_dispara_task(self, api_client: APIClient) -> None:
        """Em cache hit, devolve o valor cacheado e não dispara task."""
        payload = {
            "count": 1,
            "total_count": 1,
            "projects": [
                {
                    "id": "guid-1",
                    "name": "SME - Sustentação",
                    "description": None,
                    "url": None,
                    "state": "wellFormed",
                    "revision": 42,
                    "visibility": "private",
                    "last_update_time": None,
                }
            ],
            "continuation_token": None,
            "has_more": False,
        }
        cache.set(
            azure_cache.chave_projetos(_ORGANIZACAO, 100, 0, None), payload
        )

        with patch(_DELAY) as mock_delay:
            response = _get(api_client)

        mock_delay.assert_not_called()
        assert response.json() == payload

    def test_organizacao_nao_resolvida(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem organização no request nem no ambiente, retorna 400."""
        settings.AZURE_DEVOPS_ORGANIZATION = ""

        response = _get(api_client)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
