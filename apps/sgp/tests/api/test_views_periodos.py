"""Testes da view de períodos do SGP."""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.sgp.constants import CHAVE_CACHE_PERIODOS

_PERIODOS = {
    "periodos": [
        {
            "ano_letivo": 2026,
            "segmento": "eja",
            "semestre": 2,
            "bimestre": 1,
            "inicio": "2026-07-27",
            "fim": "2026-09-30",
        }
    ]
}


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestPeriodosSgpView:
    """Testes cobrindo GET /api/v1/sgp/periodos/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(reverse("sgp:periodos"))

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_cache_hit_devolve_periodos(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache hit, devolve as opções sem disparar a task."""
        settings.API_KEY = "chave-correta"
        cache.set(CHAVE_CACHE_PERIODOS, _PERIODOS)

        with patch("apps.sgp.tasks.atualizar_periodos.delay") as mock_delay:
            response = api_client.get(
                reverse("sgp:periodos"), HTTP_X_API_KEY="chave-correta"
            )

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json() == _PERIODOS
        mock_delay.assert_not_called()

    def test_cache_miss_dispara_task_e_devolve_nulo(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache miss, dispara a task e devolve ``periodos`` nulo."""
        settings.API_KEY = "chave-correta"

        with patch("apps.sgp.tasks.atualizar_periodos.delay") as mock_delay:
            response = api_client.get(
                reverse("sgp:periodos"), HTTP_X_API_KEY="chave-correta"
            )

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json() == {"periodos": None}
        mock_delay.assert_called_once_with()
