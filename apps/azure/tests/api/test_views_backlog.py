"""Testes da view de backlog do Azure DevOps."""

from typing import Any
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.azure import cache as azure_cache

_CHAVE = "chave-correta"
_ORGANIZACAO = "SME-Spassu"
_PROJETO = "SME - Sustentação"


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


@pytest.fixture
def _configurar(settings) -> None:
    """Configura API Key e organização padrão para os testes da view."""
    settings.API_KEY = _CHAVE
    settings.AZURE_DEVOPS_ORGANIZATION = _ORGANIZACAO


def _url() -> str:
    """Monta a URL da view de backlog."""
    return reverse("azure:backlog")


def _get(api_client: APIClient, **params: Any) -> Any:
    """Faz um GET autenticado na view de backlog.

    Args:
        api_client: Cliente de teste do DRF.
        **params: Query params da requisição.

    Returns:
        A resposta HTTP.
    """
    return api_client.get(_url(), params, HTTP_X_API_KEY=_CHAVE)


def _payload_completo() -> dict[str, Any]:
    """Monta um backlog válido, como o serviço produziria.

    Returns:
        Payload já no contrato consumido pelo frontend.
    """
    return {
        "total_items": 1,
        "parents": [],
        "children": [
            {
                "id": 10,
                "title": "[SGP] Erro no login",
                "state": "Active",
                "work_item_type": "BugFix",
                "tags": None,
                "created_by": "Fulana",
                "assigned_to": None,
                "area_path": None,
                "team_project": _PROJETO,
                "iteration_path": "SME\\Sprint 10",
                "completed_work": None,
                "original_estimate": None,
                "start_date": None,
                "finish_date": None,
                "created_date": "01/03/2026",
                "changed_date": None,
                "closed_date": None,
                "parent_id": None,
                "parent_link": None,
            }
        ],
        "bug_metrics": {
            "total_cycle": 1,
            "open": 0,
            "in_progress": 1,
            "resolved": 0,
            "average_resolution": None,
        },
        "metadata": {
            "start_date": "none",
            "end_date": "none",
            "organization": _ORGANIZACAO,
            "project": _PROJETO,
            "total_parents": 0,
            "total_children": 1,
        },
    }


class TestBacklogViewValidacao:
    """Testes cobrindo a validação de entrada da view."""

    def test_exige_api_key(self, api_client: APIClient) -> None:
        """Sem API Key, a view retorna 401."""
        response = api_client.get(_url(), {"project_name": _PROJETO})

        assert response.status_code == http_status.HTTP_401_UNAUTHORIZED

    @pytest.mark.usefixtures("_configurar")
    def test_project_name_obrigatorio(self, api_client: APIClient) -> None:
        """Sem `project_name`, retorna 400 com a mensagem esperada."""
        response = _get(api_client)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.json() == {"error": "project_name é obrigatório"}

    def test_organizacao_nao_resolvida(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem organização no request nem no ambiente, retorna 400."""
        settings.API_KEY = _CHAVE
        settings.AZURE_DEVOPS_ORGANIZATION = ""

        response = _get(api_client, project_name=_PROJETO)

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "organization" in response.json()["error"]

    @pytest.mark.usefixtures("_configurar")
    def test_data_em_formato_invalido(self, api_client: APIClient) -> None:
        """Datas fora de YYYY-MM-DD retornam 400."""
        response = _get(
            api_client,
            project_name=_PROJETO,
            start_date="01/01/2026",
            end_date="2026-01-31",
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "error": "Formato de data inválido. Use YYYY-MM-DD"
        }

    @pytest.mark.usefixtures("_configurar")
    def test_mes_invalido(self, api_client: APIClient) -> None:
        """Um mês fora de 1-12 retorna 400."""
        response = _get(
            api_client, project_name=_PROJETO, year="2026", month="13"
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "error": "year e month devem formar um mês válido"
        }

    @pytest.mark.usefixtures("_configurar")
    def test_ano_nao_numerico(self, api_client: APIClient) -> None:
        """Um ano não numérico retorna 400 em vez de 500."""
        response = _get(
            api_client, project_name=_PROJETO, year="abc", month="1"
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST


@pytest.mark.usefixtures("_configurar")
class TestBacklogViewCache:
    """Testes cobrindo o padrão cache-aside da view."""

    def test_cache_hit_nao_dispara_task(self, api_client: APIClient) -> None:
        """Em cache hit, devolve o valor cacheado e não dispara task."""
        chave = azure_cache.chave_backlog(
            _ORGANIZACAO, _PROJETO, None, None, {}
        )
        cache.set(chave, _payload_completo())

        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            response = _get(api_client, project_name=_PROJETO)

        mock_delay.assert_not_called()
        assert response.json() == _payload_completo()

    def test_cache_miss_dispara_task_e_devolve_backlog_vazio(
        self, api_client: APIClient
    ) -> None:
        """Em cache miss, dispara a task e devolve o fallback seguro."""
        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            response = _get(
                api_client,
                project_name=_PROJETO,
                work_item_types="BugFix,HotFix",
            )

        mock_delay.assert_called_once_with(
            _ORGANIZACAO,
            _PROJETO,
            None,
            None,
            {"work_item_types": ["BugFix", "HotFix"]},
        )
        dados = response.json()
        assert response.status_code == http_status.HTTP_200_OK
        assert dados["total_items"] == 0
        assert dados["parents"] == []
        assert dados["children"] == []
        assert dados["bug_metrics"] == {
            "total_cycle": 0,
            "open": 0,
            "in_progress": 0,
            "resolved": 0,
            "average_resolution": None,
        }
        assert dados["metadata"]["project"] == _PROJETO

    def test_nao_duplica_disparo_com_lock_ocupado(
        self, api_client: APIClient
    ) -> None:
        """Duas requisições seguidas em cache frio disparam uma task só."""
        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            _get(api_client, project_name=_PROJETO)
            _get(api_client, project_name=_PROJETO)

        mock_delay.assert_called_once()

    def test_periodo_explicito_chega_na_task(
        self, api_client: APIClient
    ) -> None:
        """`start_date`/`end_date` válidos são repassados como vieram."""
        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            _get(
                api_client,
                project_name=_PROJETO,
                start_date="2026-01-01",
                end_date="2026-01-31",
            )

        mock_delay.assert_called_once_with(
            _ORGANIZACAO, _PROJETO, "2026-01-01", "2026-01-31", {}
        )

    def test_year_e_month_viram_periodo_na_task(
        self, api_client: APIClient
    ) -> None:
        """`year`/`month` são convertidos no primeiro e último dia do mês."""
        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            _get(api_client, project_name=_PROJETO, year="2026", month="2")

        mock_delay.assert_called_once_with(
            _ORGANIZACAO, _PROJETO, "2026-02-01", "2026-02-28", {}
        )

    def test_organizacao_do_request_prevalece(
        self, api_client: APIClient
    ) -> None:
        """A organização do query param sobrepõe a do ambiente."""
        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            _get(api_client, project_name=_PROJETO, organization="Outra-Org")

        assert mock_delay.call_args.args[0] == "Outra-Org"

    def test_filtros_diferentes_usam_chaves_diferentes(
        self, api_client: APIClient
    ) -> None:
        """Um filtro diferente é um cache miss próprio."""
        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            _get(api_client, project_name=_PROJETO, states="New")
            _get(api_client, project_name=_PROJETO, states="Active")

        assert mock_delay.call_count == 2


@pytest.mark.usefixtures("_configurar")
class TestBacklogViewPost:
    """Testes cobrindo POST /api/v1/azure/backlog/."""

    def _post(self, api_client: APIClient, corpo: dict[str, Any]) -> Any:
        """Faz um POST autenticado na view de backlog.

        Args:
            api_client: Cliente de teste do DRF.
            corpo: Corpo JSON da requisição.

        Returns:
            A resposta HTTP.
        """
        return api_client.post(
            _url(), corpo, format="json", HTTP_X_API_KEY=_CHAVE
        )

    def test_project_name_obrigatorio(self, api_client: APIClient) -> None:
        """Um corpo sem `project_name` é rejeitado com 400."""
        response = self._post(api_client, {})

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "project_name" in response.json()

    def test_filtros_do_corpo_chegam_normalizados(
        self, api_client: APIClient
    ) -> None:
        """As listas do corpo viram os mesmos filtros do GET."""
        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            self._post(
                api_client,
                {
                    "project_name": _PROJETO,
                    "filters": {
                        "work_item_types": ["BugFix", " HotFix ", ""],
                        "tags": " urgente ",
                    },
                },
            )

        mock_delay.assert_called_once_with(
            _ORGANIZACAO,
            _PROJETO,
            None,
            None,
            {"work_item_types": ["BugFix", "HotFix"], "tags": "urgente"},
        )

    def test_get_e_post_equivalentes_compartilham_o_cache(
        self, api_client: APIClient
    ) -> None:
        """Filtros equivalentes resolvem para a mesma chave de cache."""
        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            _get(
                api_client,
                project_name=_PROJETO,
                work_item_types="BugFix,HotFix",
            )
            self._post(
                api_client,
                {
                    "project_name": _PROJETO,
                    "filters": {"work_item_types": ["BugFix", "HotFix"]},
                },
            )

        mock_delay.assert_called_once()

    def test_pat_do_corpo_e_ignorado(self, api_client: APIClient) -> None:
        """O `pat` é aceito por compatibilidade, mas nunca usado."""
        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            response = self._post(
                api_client,
                {"project_name": _PROJETO, "pat": "token-do-cliente"},
            )

        assert response.status_code == http_status.HTTP_200_OK
        assert "token-do-cliente" not in str(mock_delay.call_args)

    def test_data_em_formato_invalido(self, api_client: APIClient) -> None:
        """Datas fora de YYYY-MM-DD retornam 400."""
        response = self._post(
            api_client,
            {
                "project_name": _PROJETO,
                "start_date": "01/01/2026",
                "end_date": "2026-01-31",
            },
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "error": "Formato de data inválido. Use YYYY-MM-DD"
        }

    def test_year_e_month_viram_periodo(self, api_client: APIClient) -> None:
        """`year`/`month` numéricos também funcionam no corpo."""
        with patch("apps.azure.tasks.atualizar_backlog.delay") as mock_delay:
            self._post(
                api_client,
                {"project_name": _PROJETO, "year": 2026, "month": 2},
            )

        mock_delay.assert_called_once_with(
            _ORGANIZACAO, _PROJETO, "2026-02-01", "2026-02-28", {}
        )

    def test_organizacao_nao_resolvida(
        self, api_client: APIClient, settings
    ) -> None:
        """Sem organização no corpo nem no ambiente, retorna 400."""
        settings.AZURE_DEVOPS_ORGANIZATION = ""

        response = self._post(api_client, {"project_name": _PROJETO})

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "organization" in response.json()["error"]

    def test_cache_hit_devolve_o_payload(self, api_client: APIClient) -> None:
        """Em cache hit, o POST devolve o mesmo payload do GET."""
        cache.set(
            azure_cache.chave_backlog(_ORGANIZACAO, _PROJETO, None, None, {}),
            _payload_completo(),
        )

        response = self._post(api_client, {"project_name": _PROJETO})

        assert response.json() == _payload_completo()
