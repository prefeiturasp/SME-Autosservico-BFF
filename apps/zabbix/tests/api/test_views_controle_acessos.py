"""Testes das views de controle de acessos do SGP."""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.zabbix import cache as zabbix_cache

_ESTADO = {
    "atualizado_em": "2026-11-10T09:30:00-03:00",
    "limite_conexoes": 5000,
    "conectados": {"total": 6467, "sgp": 6400, "sondagem": 67},
    "em_fila": 1467,
    "fila_iniciada_em": "2026-11-10T07:41:00-03:00",
    "tempo_espera_estimado": {
        "media_s": 350.0,
        "posicao_media": 8,
        "testes": 2,
        "atingiu_limite_teste": True,
    },
}

_SERIE = {
    "granularidade": "hora",
    "atualizado_em": "2026-11-10T09:30:00-03:00",
    "pontos": [
        {
            "inicio": "2026-11-10T08:00:00-03:00",
            "total": 5100,
            "em_fila_max": 100,
            "fila_ativa": True,
        }
    ],
}


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestControleAcessosSgpView:
    """Testes cobrindo GET /api/v1/zabbix/sgp/controle-acessos/."""

    def _url(self) -> str:
        return reverse("zabbix:sgp-controle-acessos")

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(self._url())

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_cache_hit_devolve_estado(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache hit, devolve o estado sem disparar a task."""
        settings.API_KEY = "chave-correta"
        cache.set(zabbix_cache.chave_controle_acessos(), _ESTADO)

        with patch(
            "apps.zabbix.tasks.atualizar_controle_acessos.delay"
        ) as mock_delay:
            response = api_client.get(
                self._url(), HTTP_X_API_KEY="chave-correta"
            )

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json() == _ESTADO
        mock_delay.assert_not_called()

    def test_cache_miss_dispara_task_e_devolve_nulos(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache miss, dispara a task e devolve os campos nulos."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.zabbix.tasks.atualizar_controle_acessos.delay"
        ) as mock_delay:
            response = api_client.get(
                self._url(), HTTP_X_API_KEY="chave-correta"
            )

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json()["limite_conexoes"] is None
        assert response.json()["tempo_espera_estimado"] is None
        mock_delay.assert_called_once_with()


class TestSerieAcessosSgpView:
    """Testes cobrindo GET /api/v1/zabbix/sgp/controle-acessos/serie/."""

    def _url(self) -> str:
        return reverse("zabbix:sgp-controle-acessos-serie")

    def test_granularidade_obrigatoria_e_valida(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem granularidade, ou com uma desconhecida, retorna 400."""
        settings.API_KEY = "chave-correta"

        sem = api_client.get(self._url(), HTTP_X_API_KEY="chave-correta")
        invalida = api_client.get(
            self._url(),
            {"granularidade": "semana"},
            HTTP_X_API_KEY="chave-correta",
        )

        assert sem.status_code == http_status.HTTP_400_BAD_REQUEST
        assert invalida.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "granularidade" in invalida.json()

    def test_cache_hit_devolve_serie(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache hit, devolve a série da granularidade pedida."""
        settings.API_KEY = "chave-correta"
        cache.set(zabbix_cache.chave_serie_acessos("hora"), _SERIE)

        with patch(
            "apps.zabbix.tasks.atualizar_serie_controle_acessos.delay"
        ) as mock_delay:
            response = api_client.get(
                self._url(),
                {"granularidade": "hora"},
                HTTP_X_API_KEY="chave-correta",
            )

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json() == _SERIE
        mock_delay.assert_not_called()

    def test_cache_miss_dispara_task_e_devolve_vazia(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache miss, dispara a task da granularidade e devolve vazio."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.zabbix.tasks.atualizar_serie_controle_acessos.delay"
        ) as mock_delay:
            response = api_client.get(
                self._url(),
                {"granularidade": "mes"},
                HTTP_X_API_KEY="chave-correta",
            )

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json() == {
            "granularidade": "mes",
            "atualizado_em": None,
            "pontos": [],
        }
        mock_delay.assert_called_once_with("mes")
