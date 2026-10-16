"""Testes da view de resumo de build do Jenkins."""

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
    """Monta a URL da view de resumo de build do Jenkins."""
    return reverse("zabbix:jenkins-job")


class TestJenkinsJobSummaryView:
    """Testes cobrindo GET /api/v1/zabbix/jenkins/job/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(_url(), {"project": "meu-job"})

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_project_obrigatorio(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem `project`, retorna 400 com a mensagem esperada."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(_url(), HTTP_X_API_KEY="chave-correta")

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "project é obrigatório"}

    def test_env_homolog_e_reconhecido(
        self, api_client: APIClient, settings
    ) -> None:
        """`env=homolog` seleciona o ambiente homolog."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.zabbix.tasks.atualizar_jenkins_job.delay"
        ) as mock_delay:
            api_client.get(
                _url(),
                {"project": "meu-job", "env": "homolog"},
                HTTP_X_API_KEY="chave-correta",
            )

        mock_delay.assert_called_once_with("meu-job", "homolog")

    def test_env_default_e_prod(self, api_client: APIClient, settings) -> None:
        """Sem `env`, o ambiente default é prod."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.zabbix.tasks.atualizar_jenkins_job.delay"
        ) as mock_delay:
            api_client.get(
                _url(),
                {"project": "meu-job"},
                HTTP_X_API_KEY="chave-correta",
            )

        mock_delay.assert_called_once_with("meu-job", "prod")

    def test_cache_hit_nao_dispara_task(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache hit, devolve o valor cacheado e não dispara task."""
        settings.API_KEY = "chave-correta"
        chave = zabbix_cache.chave_jenkins("meu-job", "prod")
        cache.set(
            chave,
            {
                "lastBuild": {
                    "number": 7,
                    "status": "SUCCESS",
                    "timestampMs": 1.0,
                    "timestamp": "01/01/2024 10:00",
                    "durationMs": 1000.0,
                    "duration": "1s",
                }
            },
        )

        with patch(
            "apps.zabbix.tasks.atualizar_jenkins_job.delay"
        ) as mock_delay:
            response = api_client.get(
                _url(),
                {"project": "meu-job"},
                HTTP_X_API_KEY="chave-correta",
            )

        mock_delay.assert_not_called()
        assert response.json()["lastBuild"]["number"] == 7

    def test_cache_miss_dispara_task_e_devolve_vazio(
        self, api_client: APIClient, settings
    ) -> None:
        """Em cache miss, dispara a task e devolve um resumo vazio."""
        settings.API_KEY = "chave-correta"

        with patch(
            "apps.zabbix.tasks.atualizar_jenkins_job.delay"
        ) as mock_delay:
            response = api_client.get(
                _url(),
                {"project": "meu-job"},
                HTTP_X_API_KEY="chave-correta",
            )

        mock_delay.assert_called_once_with("meu-job", "prod")
        assert response.json() == {}
