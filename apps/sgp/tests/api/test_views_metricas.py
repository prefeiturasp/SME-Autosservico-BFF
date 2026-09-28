"""Testes da view de métricas do SGP."""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.sgp.constants import chave_cache_metricas


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


def _url() -> str:
    """Monta a URL da view de métricas do SGP."""
    return reverse("sgp:metricas")


_PARAMS = {"ano_letivo": 2026, "bimestre": 2}

_CONTRATO = {
    "atualizado_em": "2026-08-25T10:00:00-03:00",
    "ano_letivo": 2026,
    "bimestre": 2,
    "usuarios": {
        "com_acesso_ativo": {"valor": 8398, "variacao_30_dias": 453},
        "de_unidades_educacionais": {
            "total": 200,
            "diretorias_regionais": 13,
        },
        "unicos_por_dia": None,
        "acessos_por_hora": None,
    },
    "frequencias": {"lancadas": 18432, "esperadas": 21760, "percentual": 84.7},
    "sondagens": {"realizadas": 1243, "esperadas": 2683},
    "fechamento": {
        "nao_iniciados": 8398,
        "processado_sucesso": 7530,
        "processado_pendencias": 6853,
        "processado_erro": 12398,
    },
    "conselho_classe": {
        "nao_iniciados": 204,
        "em_andamento": 387,
        "processado_sucesso": 1889,
    },
}


class TestMetricasSgpView:
    """Testes cobrindo GET /api/v1/sgp/metricas/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(_url(), _PARAMS)

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_parametros_obrigatorios(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem ano_letivo/bimestre, a view retorna 400."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(_url(), HTTP_X_API_KEY="chave-correta")

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_cache_hit_devolve_valor_sem_disparar_task(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache hit, devolve o contrato cacheado e não dispara task."""
        settings.API_KEY = "chave-correta"
        cache.set(chave_cache_metricas(2026, 2), _CONTRATO)

        with patch("apps.sgp.tasks.atualizar_metricas.delay") as mock_delay:
            response = api_client.get(
                _url(), _PARAMS, HTTP_X_API_KEY="chave-correta"
            )

        assert response.status_code == http_status.HTTP_200_OK
        corpo = response.json()
        assert corpo["frequencias"] == {
            "lancadas": 18432,
            "esperadas": 21760,
            "percentual": 84.7,
        }
        mock_delay.assert_not_called()

    def test_cache_miss_dispara_task_e_devolve_fallback(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache miss, dispara a task com o período e devolve fallback."""
        settings.API_KEY = "chave-correta"

        with patch("apps.sgp.tasks.atualizar_metricas.delay") as mock_delay:
            response = api_client.get(
                _url(), _PARAMS, HTTP_X_API_KEY="chave-correta"
            )

        assert response.status_code == http_status.HTTP_200_OK
        mock_delay.assert_called_once_with(2026, 2)
        corpo = response.json()
        assert corpo["frequencias"] is None
        assert corpo["ano_letivo"] == 2026
