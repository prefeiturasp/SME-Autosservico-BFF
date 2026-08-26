"""Testes da view de disponibilidade dos ambientes por sistema."""

from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient


def _url() -> str:
    """Monta a URL da view de disponibilidade dos sistemas."""
    return reverse("zabbix:disponibilidade-sistemas")


class TestSistemasDisponibilidadeView:
    """Testes cobrindo GET /api/v1/zabbix/disponibilidade/sistemas/."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(_url())

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_lista_sistema_com_producao_e_homologacao(
        self, api_client: APIClient, settings
    ) -> None:
        """Sistema com HOM traz ``producao`` e ``homologacao``."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(_url(), HTTP_X_API_KEY="chave-correta")

        assert response.status_code == http_status.HTTP_200_OK
        por_sistema = {item["sistema"]: item for item in response.json()}
        assert por_sistema["Serap"] == {
            "sistema": "Serap",
            "producao": "PRD - Serap",
            "homologacao": "HOM - Serap",
        }
        assert por_sistema["Novo SGP"]["homologacao"] == "HOM - NovoSGP"

    def test_sistema_sem_homologacao_omite_a_chave(
        self, api_client: APIClient, settings
    ) -> None:
        """Sistema sem HOM não traz a chave ``homologacao``."""
        settings.API_KEY = "chave-correta"

        response = api_client.get(_url(), HTTP_X_API_KEY="chave-correta")

        por_sistema = {item["sistema"]: item for item in response.json()}
        assert "homologacao" not in por_sistema["Escolhas"]
        assert por_sistema["Escolhas"]["producao"] == "PRD - Escolhas"
