"""Testes da view de métricas do SIGPAE."""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.sigpae.constants import CHAVE_CACHE_METRICAS


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


def _url() -> str:
    """Monta a URL da view de métricas do SIGPAE."""
    return reverse("sigpae:metricas")


_CONTRATO = {
    "atualizado_em": "2026-08-25T10:00:00-03:00",
    "usuarios": {
        "com_acesso_ativo": {"total": 10, "ativos_30_dias": 4},
        "unicos_por_dia": None,
        "acessos_hoje": None,
        "por_tipo_perfil": {"codae": 3, "dre": 0, "ue": 0, "empresa": 0},
        "comparativo_acessos": None,
    },
    "alimentacao_terceirizada": {
        "medicoes_iniciais": {
            "aguardando_envio_ue": None,
            "enviadas_pelas_unidades": None,
            "aprovadas_pelas_dres": None,
            "aguardando_codae": None,
            "aprovadas_codae": None,
        }
    },
}


class TestMetricasSigpaeView:
    """Testes cobrindo GET /api/v1/sigpae/metricas/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(_url())

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_cache_hit_devolve_valor_sem_disparar_task(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache hit, devolve o contrato cacheado e não dispara task."""
        settings.API_KEY = "chave-correta"
        cache.set(CHAVE_CACHE_METRICAS, _CONTRATO)

        with patch("apps.sigpae.tasks.atualizar_metricas.delay") as mock_delay:
            response = api_client.get(_url(), HTTP_X_API_KEY="chave-correta")

        assert response.status_code == http_status.HTTP_200_OK
        corpo = response.json()
        assert corpo["usuarios"]["com_acesso_ativo"] == {
            "total": 10,
            "ativos_30_dias": 4,
        }
        mock_delay.assert_not_called()

    def test_cache_miss_dispara_task_e_devolve_fallback(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache miss, dispara a task e devolve o fallback nulo."""
        settings.API_KEY = "chave-correta"

        with patch("apps.sigpae.tasks.atualizar_metricas.delay") as mock_delay:
            response = api_client.get(_url(), HTTP_X_API_KEY="chave-correta")

        assert response.status_code == http_status.HTTP_200_OK
        mock_delay.assert_called_once_with()
        assert response.json()["usuarios"]["com_acesso_ativo"] is None
