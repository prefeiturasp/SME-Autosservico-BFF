"""Testes da view de status de banco de dados."""

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


def _url() -> str:
    """Monta a URL da view de status de banco de dados."""
    return reverse("zabbix:database")


class TestDatabaseStatusView:
    """Testes cobrindo GET /api/v1/zabbix/database/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(_url(), {"system": "Novo SGP"})

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_system_obrigatorio(self, api_client: APIClient, settings) -> None:
        """Sem `system`, retorna 400 com a mensagem esperada."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(_url(), HTTP_X_API_KEY="chave-correta")

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "system é obrigatório"}

    def test_sistema_sem_banco_responde_instantaneo_sem_task(
        self, api_client: APIClient, settings
    ) -> None:
        """O sistema "Escolhas" responde na hora, sem cache nem Celery."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.zabbix.tasks.atualizar_status_banco_sistema.delay"
        ) as mock_delay:
            response = api_client.get(
                _url(),
                {"system": "Escolhas"},
                HTTP_X_API_KEY="chave-correta",
            )

        mock_delay.assert_not_called()
        assert response.json() == {
            "system": "Escolhas",
            "hasDatabase": False,
            "instances": [],
        }

    def test_sistema_desconhecido_responde_instantaneo(
        self, api_client: APIClient, settings
    ) -> None:
        """Um sistema fora do dicionário também responde na hora."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.zabbix.tasks.atualizar_status_banco_sistema.delay"
        ) as mock_delay:
            response = api_client.get(
                _url(),
                {"system": "Sistema Que Não Existe"},
                HTTP_X_API_KEY="chave-correta",
            )

        mock_delay.assert_not_called()
        assert response.json()["hasDatabase"] is False

    def test_cache_hit_nao_dispara_task(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache hit, devolve o valor cacheado e não dispara task."""
        settings.API_KEY = "chave-correta"
        chave = zabbix_cache.chave_database("Novo SGP")
        cache.set(
            chave,
            {
                "system": "Novo SGP",
                "hasDatabase": True,
                "instances": [
                    {
                        "label": "PostgreSQL (Escrita)",
                        "dbType": "postgresql",
                        "available": True,
                        "role": "escrita",
                    }
                ],
            },
        )

        with patch(
            "apps.zabbix.tasks.atualizar_status_banco_sistema.delay"
        ) as mock_delay:
            response = api_client.get(
                _url(),
                {"system": "Novo SGP"},
                HTTP_X_API_KEY="chave-correta",
            )

        mock_delay.assert_not_called()
        assert response.json()["instances"][0]["available"] is True

    def test_cache_miss_dispara_task_e_devolve_fallback_indisponivel(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache miss, dispara a task e devolve instâncias indisponíveis."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.zabbix.tasks.atualizar_status_banco_sistema.delay"
        ) as mock_delay:
            response = api_client.get(
                _url(),
                {"system": "Novo SGP"},
                HTTP_X_API_KEY="chave-correta",
            )

        mock_delay.assert_called_once_with("Novo SGP")
        dados = response.json()
        assert dados["hasDatabase"] is True
        assert all(
            not instancia["available"] for instancia in dados["instances"]
        )
        assert {i["role"] for i in dados["instances"]} == {
            "escrita",
            "leitura",
        }
