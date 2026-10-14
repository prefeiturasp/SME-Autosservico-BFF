"""Testes da view de status de disponibilidade (presets producao/filas)."""

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.zabbix import cache as zabbix_cache


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


def _url(preset: str = "producao") -> str:
    """Monta a URL da view para um preset específico."""
    return reverse("zabbix:status-preset", kwargs={"preset": preset})


class TestStatusPresetView:
    """Testes cobrindo GET /api/v1/zabbix/status/<preset>/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(_url(), {"project": "meu-projeto"})

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_project_obrigatorio(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem `project`, retorna 400 com a mensagem esperada."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(_url(), HTTP_X_API_KEY="chave-correta")

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "project é obrigatório"}

    def test_preset_invalido(self, api_client: APIClient, settings) -> None:
        """Um preset desconhecido retorna 400."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(
            _url("inexistente"),
            {"project": "meu-projeto"},
            HTTP_X_API_KEY="chave-correta",
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "preset inválido"}

    def test_preset_e_normalizado_para_minusculas(
        self, api_client: APIClient, settings
    ) -> None:
        """O preset do path é normalizado com `.lower()`."""
        settings.API_KEY = "chave-correta"

        with patch("apps.zabbix.tasks.atualizar_status.delay") as mock_delay:
            response = api_client.get(
                _url("PRODUCAO"),
                {"project": "meu-projeto"},
                HTTP_X_API_KEY="chave-correta",
            )

        assert response.status_code == http_status.HTTP_200_OK
        mock_delay.assert_called_once_with(
            "producao", "Zabbix server", "meu-projeto"
        )

    def test_host_usa_default_quando_ausente(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem `host`, usa o ZABBIX_DEFAULT_HOST configurado."""
        settings.API_KEY = "chave-correta"
        settings.ZABBIX_DEFAULT_HOST = "Host Padrão"

        with patch("apps.zabbix.tasks.atualizar_status.delay") as mock_delay:
            api_client.get(
                _url(),
                {"project": "meu-projeto"},
                HTTP_X_API_KEY="chave-correta",
            )

        mock_delay.assert_called_once_with(
            "producao", "Host Padrão", "meu-projeto"
        )

    def test_cache_hit_nao_dispara_task(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache hit, devolve o valor cacheado e não dispara task."""
        settings.API_KEY = "chave-correta"
        chave = zabbix_cache.chave_status(
            "producao", "Zabbix server", "meu-projeto"
        )
        cache.set(
            chave,
            {
                "available": False,
                "incidents_recent": True,
                "message": "Há incidentes ativos",
                "lastIncidentAt": "01/01/2024 10:00",
            },
        )

        with patch("apps.zabbix.tasks.atualizar_status.delay") as mock_delay:
            response = api_client.get(
                _url(),
                {"project": "meu-projeto"},
                HTTP_X_API_KEY="chave-correta",
            )

        mock_delay.assert_not_called()
        dados = response.json()
        assert dados["available"] is False
        assert dados["message"] == "Há incidentes ativos"

    def test_cache_miss_dispara_task_e_devolve_fallback(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache miss, dispara a task e devolve o fallback seguro."""
        settings.API_KEY = "chave-correta"

        with patch("apps.zabbix.tasks.atualizar_status.delay") as mock_delay:
            response = api_client.get(
                _url(),
                {"project": "meu-projeto", "host": "meu-host"},
                HTTP_X_API_KEY="chave-correta",
            )

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json() == {
            "available": True,
            "incidents_recent": False,
            "message": "Sem incidentes recentes",
        }
        mock_delay.assert_called_once_with(
            "producao", "meu-host", "meu-projeto"
        )
