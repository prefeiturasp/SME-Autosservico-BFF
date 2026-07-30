"""Testes do serviço de listagem de projetos do Azure DevOps."""

from unittest.mock import patch

from apps.azure.services.projetos import montar_projetos_vazio
from apps.azure.services.projetos import obter_projetos

_CAMINHO_REQUEST = (
    "apps.azure.services.projetos.client.azure_request_com_cabecalhos"
)


class TestMontarProjetosVazio:
    """Testes cobrindo o payload de listagem vazia."""

    def test_estrutura_do_fallback(self) -> None:
        """O fallback preserva todas as chaves do contrato."""
        assert montar_projetos_vazio() == {
            "count": 0,
            "total_count": None,
            "projects": [],
            "continuation_token": None,
            "has_more": False,
        }


class TestObterProjetos:
    """Testes cobrindo obter_projetos()."""

    def test_converte_os_projetos_e_conta(self) -> None:
        """Os campos do Azure viram o formato de saída, com contagem."""
        corpo = {
            "count": 2,
            "value": [
                {
                    "id": "guid-1",
                    "name": "SME - Sustentação",
                    "description": "Projeto de sustentação",
                    "url": "https://dev.azure.com/_apis/projects/guid-1",
                    "state": "wellFormed",
                    "revision": 42,
                    "visibility": "private",
                    "lastUpdateTime": "2026-03-09T13:45:12Z",
                },
                {"id": "guid-2", "name": "Outro"},
            ],
        }

        with patch(_CAMINHO_REQUEST, return_value=(corpo, {})):
            resultado = obter_projetos("org")

        assert resultado["count"] == 2
        assert resultado["total_count"] == 2
        assert resultado["has_more"] is False
        assert resultado["continuation_token"] is None
        assert resultado["projects"][0] == {
            "id": "guid-1",
            "name": "SME - Sustentação",
            "description": "Projeto de sustentação",
            "url": "https://dev.azure.com/_apis/projects/guid-1",
            "state": "wellFormed",
            "revision": 42,
            "visibility": "private",
            "last_update_time": "2026-03-09T13:45:12Z",
        }
        assert resultado["projects"][1]["description"] is None
        assert resultado["projects"][1]["revision"] is None

    def test_token_de_continuacao_liga_has_more(self) -> None:
        """O header de continuação vira continuation_token e has_more."""
        cabecalhos = {"x-ms-continuationtoken": "proxima-pagina"}

        with patch(_CAMINHO_REQUEST, return_value=({"value": []}, cabecalhos)):
            resultado = obter_projetos("org")

        esperado = "proxima-pagina"
        assert resultado["continuation_token"] == esperado
        assert resultado["has_more"] is True

    def test_repassa_a_paginacao_ao_azure(self) -> None:
        """top, skip e o token viram query params da chamada."""
        with patch(
            _CAMINHO_REQUEST, return_value=({"value": []}, {})
        ) as mock_request:
            obter_projetos(
                "org",
                top=50,
                skip=100,
                token_continuacao="tk",  # noqa: S106
            )

        _args, kwargs = mock_request.call_args
        assert kwargs["params"]["$top"] == 50
        assert kwargs["params"]["$skip"] == 100
        assert kwargs["params"]["continuationToken"] == "tk"

    def test_sem_token_nao_envia_o_param(self) -> None:
        """Sem token, o param de continuação não é enviado."""
        with patch(
            _CAMINHO_REQUEST, return_value=({"value": []}, {})
        ) as mock_request:
            obter_projetos("org")

        _args, kwargs = mock_request.call_args
        assert "continuationToken" not in kwargs["params"]
