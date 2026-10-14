"""Testes da view de métricas do Intranet."""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.intranet.constants import chave_cache_metricas


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


def _url() -> str:
    """Monta a URL da view de métricas do Intranet."""
    return reverse("intranet:metricas")


def _itens() -> list[dict[str, object]]:
    """Monta um card de distribuição de exemplo."""
    return [{"label": "Servidores", "value": 10}]


_KPI = {"valor": 120, "tendencia": None, "tendencia_label": None}

_CONTRATO = {
    "atualizado_em": "2026-10-09T10:00:00-03:00",
    "periodo": "geral",
    "mes": None,
    "kpis": {
        "acesso_ativo": _KPI,
        "usuarios_unicos": _KPI,
        "acessos_hoje": _KPI,
    },
    "sorteios": {
        "status_geral": {
            "cadastrados": 40,
            "realizados": 30,
            "ativos": 5,
            "encerrados": 35,
        },
        "por_tipo": _itens(),
        "por_ganhador": _itens(),
        "por_dre": _itens(),
    },
    "ordem_inscricao": {
        "status_geral": {"cadastrados": 12, "ativos": 2, "encerrados": 10},
        "por_tipo": _itens(),
        "por_ganhador": _itens(),
        "por_dre": _itens(),
    },
    "oportunidades": {
        "cadastradas": 8,
        "cvs_cadastrados": 300,
        "inscricoes_realizadas": 150,
        "contratacoes_efetivadas": 4,
    },
}


class TestMetricasIntranetView:
    """Testes cobrindo GET /api/v1/intranet/metricas/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(_url())

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "params",
        [{"periodo": "semestre"}, {"mes": "2026-13"}, {"mes": "09/2026"}],
    )
    def test_parametro_invalido(
        self, api_client: APIClient, settings, params: dict[str, str]
    ) -> None:
        """Um período fora do catálogo ou mês mal formatado retorna 400."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.intranet.tasks.atualizar_metricas.delay"
        ) as mock_delay:
            response = api_client.get(
                _url(), params, HTTP_X_API_KEY="chave-correta"
            )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        mock_delay.assert_not_called()

    def test_cache_hit_devolve_valor_sem_disparar_task(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache hit, devolve o contrato cacheado e não dispara task."""
        settings.API_KEY = "chave-correta"
        cache.set(chave_cache_metricas("geral", None), _CONTRATO)

        with patch(
            "apps.intranet.tasks.atualizar_metricas.delay"
        ) as mock_delay:
            response = api_client.get(_url(), HTTP_X_API_KEY="chave-correta")

        assert response.status_code == http_status.HTTP_200_OK
        corpo = response.json()
        assert corpo["oportunidades"]["cvs_cadastrados"] == 300
        assert corpo["sorteios"]["por_dre"] == _itens()
        mock_delay.assert_not_called()

    def test_cache_miss_sem_params_usa_padrao(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem params, dispara a task com ``geral``/sem mês e faz fallback."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.intranet.tasks.atualizar_metricas.delay"
        ) as mock_delay:
            response = api_client.get(_url(), HTTP_X_API_KEY="chave-correta")

        assert response.status_code == http_status.HTTP_200_OK
        mock_delay.assert_called_once_with("geral", None)
        corpo = response.json()
        assert corpo["periodo"] == "geral"
        assert corpo["mes"] is None
        assert corpo["kpis"] is None

    def test_cache_miss_repassa_periodo_e_mes(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache miss, dispara a task com o recorte pedido."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.intranet.tasks.atualizar_metricas.delay"
        ) as mock_delay:
            response = api_client.get(
                _url(),
                {"periodo": "mes", "mes": "2026-09"},
                HTTP_X_API_KEY="chave-correta",
            )

        assert response.status_code == http_status.HTTP_200_OK
        mock_delay.assert_called_once_with("mes", "2026-09")
        corpo = response.json()
        assert corpo["periodo"] == "mes"
        assert corpo["mes"] == "2026-09"
        assert corpo["sorteios"] is None
