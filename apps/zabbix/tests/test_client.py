"""Testes do cliente JSON-RPC do Zabbix."""

from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from apps.zabbix.client import ZabbixRpcError
from apps.zabbix.client import zabbix_rpc


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


class TestZabbixRpc:
    """Testes cobrindo zabbix_rpc()."""

    def test_monta_corpo_e_headers_corretos(self, settings) -> None:
        """O corpo e os headers seguem o envelope JSON-RPC 2.0 esperado."""
        settings.ZABBIX_API_URL = "http://zabbix.local/api_jsonrpc.php"
        settings.ZABBIX_API_TOKEN = "token-123"  # noqa: S105
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.return_value = None
        resposta.json.return_value = {"jsonrpc": "2.0", "result": [], "id": 1}

        with patch("httpx.Client") as mock_cls:
            mock_client = _mock_cliente(mock_cls, resposta)
            resultado = zabbix_rpc("trigger.get", {"filter": {}})

        assert resultado == []
        _url, kwargs = mock_client.post.call_args
        assert kwargs["json"] == {
            "jsonrpc": "2.0",
            "method": "trigger.get",
            "params": {"filter": {}},
            "id": 1,
        }
        assert kwargs["headers"] == {
            "Content-Type": "application/json-rpc",
            "Authorization": "Bearer token-123",
        }

    def test_retorna_o_campo_result(self) -> None:
        """O valor de retorno é o campo `result` do envelope JSON-RPC."""
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.return_value = None
        resposta.json.return_value = {"result": {"itemid": "1"}}

        with patch("httpx.Client") as mock_cls:
            _mock_cliente(mock_cls, resposta)
            resultado = zabbix_rpc("item.get", {})

        assert resultado == {"itemid": "1"}

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
                zabbix_rpc("trigger.get", {}, max_tentativas=3)

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
                zabbix_rpc("trigger.get", {}, max_tentativas=2)

        assert mock_client.post.call_count == 2
        assert mock_sleep.call_count == 1

    def test_nao_repete_em_status_nao_transitorio(self) -> None:
        """Status HTTP não-transitório (404) não é retentado."""
        resposta_erro = MagicMock(spec=httpx.Response)
        resposta_erro.status_code = 404
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
                zabbix_rpc("trigger.get", {})

        assert mock_client.post.call_count == 1
        mock_sleep.assert_not_called()

    def test_erro_de_negocio_sem_retry(self) -> None:
        """Um envelope com `error` levanta ZabbixRpcError, sem retry."""
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.return_value = None
        resposta.json.return_value = {
            "error": {"code": -32602, "message": "Parâmetro inválido"}
        }

        with (
            patch("httpx.Client") as mock_cls,
            patch("time.sleep") as mock_sleep,
        ):
            mock_client = _mock_cliente(mock_cls, resposta)

            with pytest.raises(ZabbixRpcError, match="Zabbix -32602"):
                zabbix_rpc("trigger.get", {})

        assert mock_client.post.call_count == 1
        mock_sleep.assert_not_called()

    def test_erro_de_negocio_com_data(self) -> None:
        """A mensagem de erro inclui `data` quando presente."""
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.return_value = None
        resposta.json.return_value = {
            "error": {
                "code": -32500,
                "message": "Erro de aplicação",
                "data": "Detalhe extra",
            }
        }

        with patch("httpx.Client") as mock_cls:
            _mock_cliente(mock_cls, resposta)
            with pytest.raises(ZabbixRpcError, match="Detalhe extra"):
                zabbix_rpc("trigger.get", {})

    def test_resposta_nao_json_sem_retry(self) -> None:
        """Resposta não-JSON levanta ZabbixRpcError sem retry."""
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.return_value = None
        resposta.json.side_effect = ValueError("not json")

        with (
            patch("httpx.Client") as mock_cls,
            patch("time.sleep") as mock_sleep,
        ):
            mock_client = _mock_cliente(mock_cls, resposta)

            with pytest.raises(ZabbixRpcError, match="Resposta não-JSON"):
                zabbix_rpc("trigger.get", {})

        assert mock_client.post.call_count == 1
        mock_sleep.assert_not_called()

    def test_resposta_string_e_tratada_como_nao_json(self) -> None:
        """Uma resposta JSON válida, mas que é string, é rejeitada."""
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.return_value = None
        resposta.json.return_value = "<html>erro</html>"

        with patch("httpx.Client") as mock_cls:
            _mock_cliente(mock_cls, resposta)
            with pytest.raises(ZabbixRpcError, match="Resposta não-JSON"):
                zabbix_rpc("trigger.get", {})
