"""Testes da view de métricas do GIPE."""

from typing import Any
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.gipe.constants import chave_cache_metricas


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


def _url() -> str:
    """Monta a URL da view de métricas do GIPE."""
    return reverse("gipe:metricas")


# Recorte do contrato real de homologação (ano 2026), com os nulos que o
# backend manda quando não há fonte: prazos, tendências e KPIs sem login.
_CONTRATO: dict[str, Any] = {
    "atualizado_em": "2026-10-27T15:21:25.017341+00:00",
    "ano_letivo": 2026,
    "kpis": {
        "acesso_ativo": {
            "valor": 8,
            "tendencia": "above",
            "tendencia_label": "1 novo nos últimos 30 dias",
        },
        "usuarios_unicos": {
            "valor": 0,
            "tendencia": None,
            "tendencia_label": None,
        },
        "acessos_hoje": {
            "valor": 0,
            "tendencia": None,
            "tendencia_label": None,
        },
    },
    "ocorrencias": {
        "status_geral": {
            "cadastrados": 424,
            "abertas": 86,
            "em_andamento": 308,
            "finalizadas": 30,
        },
        "tempo_resposta": {
            "tempo_medio_resolucao_dias": 2.872,
            "tendencia_resolucao": None,
            "tendencia_resolucao_label": None,
            "tempo_medio_primeira_tratativa_dias": 0.318,
            "tendencia_primeira_tratativa": "below",
            "tendencia_primeira_tratativa_label": "3% mais rápido",
        },
        "prazos_movimentacoes": {
            "dentro_do_prazo": None,
            "fora_do_prazo": None,
            "sem_movimentacao_7_dias": 387,
            "media_movimentacoes_por_ocorrencia": 1.9,
        },
        "por_dre": [{"label": "Ipiranga", "value": 120}],
        "por_unidade_educacional": [{"label": "EMEF EXEMPLO", "value": 9}],
        "por_categoria": {"patrimoniais": 223, "interpessoais": 201},
        "por_tipo_patrimonial": [{"label": "Furto", "value": 40}],
        "por_tipo_interpessoal": [{"label": "Bullying", "value": 35}],
        "por_mes": [{"label": "Janeiro/26", "valor": 1, "pico": False}],
        "por_periodo_letivo": [{"label": "1º Bimestre", "value": 80}],
        "tratadas_por_analista": [
            {
                "analista": "Analista Exemplo",
                "ocorrencias_tratadas": 17,
                "tempo_medio": "5,0 dias",
            }
        ],
        "tratadas_por_dre": [{"label": "Ipiranga", "value": 12}],
    },
    "usuarios": {
        "cadastrados": 18,
        "por_tipo_de_perfil": [
            {"label": "Diretor de Escola", "percentage": 39}
        ],
        "perfis_mais_utilizados": [{"label": "Diretor de Escola", "value": 7}],
        "por_dre": [{"label": "Ipiranga", "value": 5}],
        "por_unidade_educacional": [{"label": "EMEF EXEMPLO", "value": 2}],
    },
    "produtividade": {
        "encaminhamentos_realizados": 402,
        "anexos_enviados": 25,
        "atualizacoes_nas_ocorrencias": 826,
    },
}


def _get(
    api_client: APIClient, settings, params: dict[str, Any] | None = None
) -> Any:
    """Faz o GET autenticado pela API Key do BFF."""
    settings.API_KEY = "chave-correta"
    return api_client.get(_url(), params or {}, HTTP_X_API_KEY="chave-correta")


class TestMetricasGipeView:
    """Testes cobrindo GET /api/v1/gipe/metricas/."""

    def test_sem_api_key_responde_401(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem a API Key, a view não responde métricas."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(_url(), {"ano_letivo": 2026})

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_cache_quente_devolve_contrato(
        self, api_client: APIClient, settings
    ) -> None:
        """Com o cache quente, devolve o contrato inteiro, nulos inclusive."""
        cache.set(chave_cache_metricas(2026), _CONTRATO)

        with patch("apps.gipe.tasks.atualizar_metricas.delay") as mock_delay:
            response = _get(api_client, settings, {"ano_letivo": 2026})

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json() == _CONTRATO
        mock_delay.assert_not_called()

    def test_cache_frio_dispara_task_e_devolve_fallback(
        self, api_client: APIClient, settings
    ) -> None:
        """Com o cache frio, dispara a coleta e devolve os blocos nulos."""
        with patch("apps.gipe.tasks.atualizar_metricas.delay") as mock_delay:
            response = _get(api_client, settings, {"ano_letivo": 2026})

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json() == {
            "atualizado_em": None,
            "ano_letivo": 2026,
            "kpis": None,
            "ocorrencias": None,
            "usuarios": None,
            "produtividade": None,
        }
        mock_delay.assert_called_once_with(2026)

    def test_sem_ano_usa_o_ano_corrente(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem ``ano_letivo``, vale o ano corrente da requisição."""
        cache.set(
            chave_cache_metricas(2031), {**_CONTRATO, "ano_letivo": 2031}
        )

        with patch(
            "apps.gipe.api.views.ano_letivo_corrente", return_value=2031
        ):
            response = _get(api_client, settings)

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json()["ano_letivo"] == 2031

    @pytest.mark.parametrize("ano", ["abc", "1999", "2101"])
    def test_ano_invalido_responde_400(
        self, api_client: APIClient, settings, ano: str
    ) -> None:
        """Ano fora do formato ou da faixa não vira chave de cache."""
        with patch("apps.gipe.tasks.atualizar_metricas.delay") as mock_delay:
            response = _get(api_client, settings, {"ano_letivo": ano})

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        mock_delay.assert_not_called()
