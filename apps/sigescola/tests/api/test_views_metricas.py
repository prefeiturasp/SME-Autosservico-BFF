"""Testes da view de métricas do SIG-Escola."""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.sigescola.constants import chave_cache_metricas


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


def _url() -> str:
    """Monta a URL da view de métricas do SIG-Escola."""
    return reverse("sigescola:metricas")


_CONTRATO = {
    "atualizado_em": "2026-10-09T10:00:00-03:00",
    "filtros": {
        "periodo": "2026.2",
        "data_inicio": "2026-05-01",
        "data_fim": "2026-09-01",
        "dre": None,
        "ue": None,
    },
    "opcoes": {"periodos": ["2026.3", "2026.2"], "unidades": []},
    "usuarios": {
        "com_acesso_ativo": {"valor": 28, "variacao_30_dias": 2},
        "unicos_por_dia": {"valor": 2, "variacao_percentual_30_dias": -23.1},
        "acessos_hoje": {"valor": 2, "variacao_percentual_30_dias": -52.8},
    },
    "plano_anual_de_atividades": {
        "em_andamento": 83,
        "finalizados": 35,
        "em_retificacao": 46,
    },
    "prestacao_de_contas": {
        "ues_aptas": 1650,
        "enviadas_ou_em_andamento": 2,
        "creditos_disponiveis": 118502864.0,
        "despesas_registradas": 578497.91,
        "demonstrativos_gerados": 7,
        "devolucao_ao_tesouro": 0.0,
    },
    "situacao_patrimonial": {
        "quantidade_bens_produzidos": 7,
        "valor_bens_produzidos": 20199.9,
    },
}


class TestMetricasSigEscolaView:
    """Testes cobrindo GET /api/v1/sigescola/metricas/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(_url())

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "params",
        [
            {"periodo": "2026.2", "data_inicio": "2026-01-01"},
            {"data_inicio": "2026-01-01"},
            {"data_inicio": "2026-09-22", "data_fim": "2026-01-01"},
            {"dre": "butanta"},
        ],
    )
    def test_filtros_invalidos(
        self, api_client: APIClient, settings, params: dict[str, str]
    ) -> None:
        """Combinações ou formatos inválidos retornam 400."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(
            _url(), params, HTTP_X_API_KEY="chave-correta"
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_cache_hit_devolve_valor_sem_disparar_task(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache hit, devolve o contrato cacheado e não dispara task."""
        settings.API_KEY = "chave-correta"
        cache.set(chave_cache_metricas({"periodo": "2026.2"}), _CONTRATO)

        with patch(
            "apps.sigescola.tasks.atualizar_metricas.delay"
        ) as mock_delay:
            response = api_client.get(
                _url(), {"periodo": "2026.2"}, HTTP_X_API_KEY="chave-correta"
            )

        assert response.status_code == http_status.HTTP_200_OK
        corpo = response.json()
        assert corpo["prestacao_de_contas"]["ues_aptas"] == 1650
        assert corpo["plano_anual_de_atividades"]["finalizados"] == 35
        assert corpo["usuarios"]["acessos_hoje"] == {
            "valor": 2,
            "variacao_percentual_30_dias": -52.8,
        }
        mock_delay.assert_not_called()

    def test_cache_miss_dispara_task_e_devolve_fallback(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache miss, dispara a task com os filtros e devolve fallback."""
        settings.API_KEY = "chave-correta"
        params = {
            "data_inicio": "2026-01-01",
            "data_fim": "2026-09-22",
            "dre": "108100",
        }

        with patch(
            "apps.sigescola.tasks.atualizar_metricas.delay"
        ) as mock_delay:
            response = api_client.get(
                _url(), params, HTTP_X_API_KEY="chave-correta"
            )

        assert response.status_code == http_status.HTTP_200_OK
        mock_delay.assert_called_once_with(params)
        corpo = response.json()
        assert corpo["atualizado_em"] is None
        assert corpo["prestacao_de_contas"] is None
        assert corpo["filtros"]["dre"] == "108100"
        assert corpo["filtros"]["periodo"] is None
