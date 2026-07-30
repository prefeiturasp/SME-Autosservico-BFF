"""Testes do cliente do proxy de busca do Kibana."""

from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from apps.core.client_kibana import KibanaSearchError
from apps.core.client_kibana import kibana_search


def _mock_cliente(mock_cls: MagicMock, resposta: MagicMock) -> MagicMock:
    """Configura ``httpx.Client`` mockado como context manager.

    Args:
        mock_cls: O mock da classe ``httpx.Client``.
        resposta: A resposta que ``.post()`` deve retornar.

    Returns:
        O mock da instância do cliente.
    """
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = resposta
    mock_cls.return_value = mock_client
    return mock_client


class TestKibanaSearch:
    """Testes cobrindo kibana_search()."""

    def test_monta_url_corpo_e_auth_corretos(self, settings) -> None:
        """A URL, o corpo e a autenticação seguem o formato validado na POC."""
        settings.KIBANA_URL = "https://kibana.local/"
        settings.KIBANA_USERNAME = "usuario"
        settings.KIBANA_PASSWORD = "senha"  # noqa: S105
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.return_value = None
        resposta.json.return_value = {"rawResponse": {"hits": {"hits": []}}}

        with patch("httpx.Client") as mock_cls:
            mock_client = _mock_cliente(mock_cls, resposta)
            resultado = kibana_search("prod_metricas_sgp_acessos", {"size": 0})

        assert resultado == {"rawResponse": {"hits": {"hits": []}}}
        args, kwargs = mock_client.post.call_args
        assert args[0] == "https://kibana.local/internal/search/es"
        assert kwargs["json"] == {
            "params": {
                "index": "prod_metricas_sgp_acessos",
                "body": {"size": 0},
            }
        }
        assert kwargs["auth"] == ("usuario", "senha")

    def test_repete_em_erro_de_transporte_ate_o_limite(self) -> None:
        """Erros de transporte são retentados até o limite de tentativas."""
        with (
            patch("httpx.Client") as mock_cls,
            patch("time.sleep") as mock_sleep,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("falhou")
            mock_cls.return_value = mock_client

            with pytest.raises(httpx.ConnectError):
                kibana_search("indice", {}, max_tentativas=3)

        assert mock_client.post.call_count == 3
        assert mock_sleep.call_count == 2

    def test_repete_em_status_transitorio(self) -> None:
        """Status HTTP transitório (503) é retentado."""
        resposta_erro = MagicMock(spec=httpx.Response)
        resposta_erro.status_code = 503
        erro_http = httpx.HTTPStatusError(
            "erro", request=MagicMock(), response=resposta_erro
        )
        resposta_erro.raise_for_status.side_effect = erro_http

        with (
            patch("httpx.Client") as mock_cls,
            patch("time.sleep") as mock_sleep,
        ):
            mock_client = _mock_cliente(mock_cls, resposta_erro)

            with pytest.raises(httpx.HTTPStatusError):
                kibana_search("indice", {}, max_tentativas=2)

        assert mock_client.post.call_count == 2
        assert mock_sleep.call_count == 1

    def test_nao_repete_em_status_nao_transitorio(self) -> None:
        """Status HTTP não-transitório (401) não é retentado."""
        resposta_erro = MagicMock(spec=httpx.Response)
        resposta_erro.status_code = 401
        erro_http = httpx.HTTPStatusError(
            "erro", request=MagicMock(), response=resposta_erro
        )
        resposta_erro.raise_for_status.side_effect = erro_http

        with (
            patch("httpx.Client") as mock_cls,
            patch("time.sleep") as mock_sleep,
        ):
            mock_client = _mock_cliente(mock_cls, resposta_erro)

            with pytest.raises(httpx.HTTPStatusError):
                kibana_search("indice", {})

        assert mock_client.post.call_count == 1
        mock_sleep.assert_not_called()

    def test_resposta_nao_json_sem_retry(self) -> None:
        """Resposta não-JSON levanta KibanaSearchError sem retry."""
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.return_value = None
        resposta.json.side_effect = ValueError("not json")

        with (
            patch("httpx.Client") as mock_cls,
            patch("time.sleep") as mock_sleep,
        ):
            mock_client = _mock_cliente(mock_cls, resposta)

            with pytest.raises(KibanaSearchError, match="Resposta não-JSON"):
                kibana_search("indice", {})

        assert mock_client.post.call_count == 1
        mock_sleep.assert_not_called()
