"""Testes da view de métricas do Bens Físicos."""

from typing import Any
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.bensfisicos.constants import CHAVE_CACHE_METRICAS
from apps.bensfisicos.fallback import metricas_indisponivel

_CHAVE = "chave-correta"


@pytest.fixture(autouse=True)
def _api_key(settings) -> None:
    """Configura a API Key e começa cada teste com o cache vazio."""
    settings.API_KEY = _CHAVE
    cache.clear()


# Recorte do contrato real de homologação (10/11/2026).
_CONTRATO: dict[str, Any] = {
    "atualizado_em": "2026-11-10T09:28:14.457864+00:00",
    "usuarios": {
        "com_acesso_ativo": {"valor": 4},
        "unicos_por_dia": {"valor": 0, "variacao_percentual_30_dias": -100.0},
    },
    "cadastro_de_bens": {
        "bens_cadastrados": 6094,
        "aguardando_aprovacao": 53,
        "por_unidade_administrativa": [
            {
                "sigla": "SMECOTIC",
                "nome": "COORDENADORIA DE TECNOLOGIA DA INFORMAÇÃO",
                "bens": 493,
            }
        ],
    },
    "baixas_fisicas": {"aprovadas": 47, "aguardando_aprovacao": 0},
    "movimentacoes": {
        "realizadas": 1463,
        "pendentes": 77,
        "transferencias_realizadas": 9,
    },
}


def _get(api_client: APIClient, **headers):
    return api_client.get(reverse("bensfisicos:metricas"), **headers)


class TestMetricasBensFisicosView:
    """Testes cobrindo a view de métricas do Bens Físicos."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        assert (
            _get(api_client).status_code == http_status.HTTP_401_UNAUTHORIZED
        )

    def test_cache_quente_devolve_contrato(
        self, api_client: APIClient
    ) -> None:
        """Com o cache quente, devolve o contrato sem disparar a task."""
        cache.set(CHAVE_CACHE_METRICAS, _CONTRATO)

        with patch(
            "apps.bensfisicos.tasks.atualizar_metricas.delay"
        ) as mock_delay:
            response = _get(api_client, HTTP_X_API_KEY=_CHAVE)

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json() == _CONTRATO
        mock_delay.assert_not_called()

    def test_cache_frio_dispara_task_e_devolve_fallback(
        self, api_client: APIClient
    ) -> None:
        """Com o cache frio, dispara a task e devolve os blocos nulos."""
        with patch(
            "apps.bensfisicos.tasks.atualizar_metricas.delay"
        ) as mock_delay:
            response = _get(api_client, HTTP_X_API_KEY=_CHAVE)

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json() == metricas_indisponivel()
        mock_delay.assert_called_once_with()

    def test_fallback_tem_todos_os_blocos_nulos(self) -> None:
        """O fallback segue o contrato degradado do backend."""
        assert metricas_indisponivel() == {
            "atualizado_em": None,
            "usuarios": None,
            "cadastro_de_bens": None,
            "baixas_fisicas": None,
            "movimentacoes": None,
        }
