"""Testes do cliente HTTP do Azure DevOps."""

import base64
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from apps.azure.client import AzureApiError
from apps.azure.client import azure_request
from apps.azure.client import azure_request_com_cabecalhos
from apps.azure.client import montar_url


def _mock_cliente(mock_cls: MagicMock, resposta: MagicMock) -> MagicMock:
    """Configura ``httpx.Client`` mockado como context manager.

    Args:
        mock_cls: O mock da classe ``httpx.Client``.
        resposta: A resposta que ``.request()`` deve retornar.

    Returns:
        O mock da instância do cliente.
    """
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.request.return_value = resposta
    mock_cls.return_value = mock_client
    return mock_client


def _resposta_ok(
    corpo: object, cabecalhos: dict[str, str] | None = None
) -> MagicMock:
    """Monta uma resposta HTTP bem-sucedida com o corpo informado.

    Args:
        corpo: Valor devolvido por ``.json()``.
        cabecalhos: Headers da resposta.

    Returns:
        O mock da resposta.
    """
    resposta = MagicMock(spec=httpx.Response)
    resposta.raise_for_status.return_value = None
    resposta.json.return_value = corpo
    resposta.headers = cabecalhos or {}
    return resposta


class TestMontarUrl:
    """Testes cobrindo montar_url()."""

    def test_codifica_organizacao_e_projeto(self) -> None:
        """Espaços e acentos do projeto viram percent-encoding."""
        url = montar_url("SME-Spassu", "SME - Sustentação", "_apis/wit/wiql")

        assert url == (
            "https://dev.azure.com/SME-Spassu/"
            "SME%20-%20Sustenta%C3%A7%C3%A3o/_apis/wit/wiql"
        )

    def test_omite_o_projeto_em_recurso_de_organizacao(self) -> None:
        """Sem projeto, a URL vai direto da organização ao recurso."""
        url = montar_url("org", "", "_apis/wit/workitems")

        assert url == "https://dev.azure.com/org/_apis/wit/workitems"


class TestAzureRequest:
    """Testes cobrindo azure_request()."""

    def test_monta_headers_de_basic_auth(self, settings) -> None:
        """O PAT é enviado como HTTP Basic com usuário vazio."""
        settings.AZURE_DEVOPS_PAT = "pat-123"
        esperado = base64.b64encode(b":pat-123").decode()

        with patch("httpx.Client") as mock_cls:
            mock_client = _mock_cliente(mock_cls, _resposta_ok({"value": []}))
            azure_request("GET", "https://dev.azure.com/org/x")

        _args, kwargs = mock_client.request.call_args
        assert kwargs["headers"] == {
            "Content-Type": "application/json",
            "Authorization": f"Basic {esperado}",
        }

    def test_repassa_metodo_params_e_corpo(self) -> None:
        """Método, query params e corpo JSON chegam ao httpx."""
        with patch("httpx.Client") as mock_cls:
            mock_client = _mock_cliente(mock_cls, _resposta_ok({"ok": True}))
            resultado = azure_request(
                "POST",
                "https://dev.azure.com/org/proj/_apis/wit/wiql",
                params={"api-version": "7.0"},
                json_body={"query": "SELECT"},
            )

        assert resultado == {"ok": True}
        args, kwargs = mock_client.request.call_args
        assert args[0] == "POST"
        assert kwargs["params"] == {"api-version": "7.0"}
        assert kwargs["json"] == {"query": "SELECT"}

    def test_devolve_os_cabecalhos_da_resposta(self) -> None:
        """A variante com cabeçalhos expõe o token de continuação."""
        with patch("httpx.Client") as mock_cls:
            _mock_cliente(
                mock_cls,
                _resposta_ok({"value": []}, {"x-ms-continuationtoken": "abc"}),
            )
            corpo, cabecalhos = azure_request_com_cabecalhos(
                "GET", "https://x"
            )

        assert corpo == {"value": []}
        assert cabecalhos["x-ms-continuationtoken"] == "abc"

    def test_repete_em_erro_de_transporte_ate_o_limite(self) -> None:
        """Erros de transporte são retentados até o limite de tentativas."""
        with (
            patch("httpx.Client") as mock_cls,
            patch("time.sleep") as mock_sleep,
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.request.side_effect = httpx.ConnectError("falhou")
            mock_cls.return_value = mock_client

            with pytest.raises(httpx.ConnectError):
                azure_request("GET", "https://x", max_tentativas=3)

        assert mock_client.request.call_count == 3
        assert mock_sleep.call_count == 2

    def test_repete_em_status_transitorio(self) -> None:
        """Status HTTP transitório (503) é retentado."""
        resposta = MagicMock(spec=httpx.Response)
        resposta.status_code = 503
        resposta.raise_for_status.side_effect = httpx.HTTPStatusError(
            "erro", request=MagicMock(), response=resposta
        )

        with (
            patch("httpx.Client") as mock_cls,
            patch("time.sleep") as mock_sleep,
        ):
            mock_client = _mock_cliente(mock_cls, resposta)

            with pytest.raises(httpx.HTTPStatusError):
                azure_request("GET", "https://x", max_tentativas=2)

        assert mock_client.request.call_count == 2
        assert mock_sleep.call_count == 1

    def test_nao_repete_em_credencial_invalida(self) -> None:
        """Status HTTP não-transitório (401) não é retentado."""
        resposta = MagicMock(spec=httpx.Response)
        resposta.status_code = 401
        resposta.raise_for_status.side_effect = httpx.HTTPStatusError(
            "erro", request=MagicMock(), response=resposta
        )

        with (
            patch("httpx.Client") as mock_cls,
            patch("time.sleep") as mock_sleep,
        ):
            mock_client = _mock_cliente(mock_cls, resposta)

            with pytest.raises(httpx.HTTPStatusError):
                azure_request("GET", "https://x")

        assert mock_client.request.call_count == 1
        mock_sleep.assert_not_called()

    def test_resposta_nao_json_sem_retry(self) -> None:
        """Resposta não-JSON levanta AzureApiError sem retry."""
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.return_value = None
        resposta.json.side_effect = ValueError("not json")

        with (
            patch("httpx.Client") as mock_cls,
            patch("time.sleep") as mock_sleep,
        ):
            mock_client = _mock_cliente(mock_cls, resposta)

            with pytest.raises(AzureApiError, match="Resposta não-JSON"):
                azure_request("GET", "https://x")

        assert mock_client.request.call_count == 1
        mock_sleep.assert_not_called()

    def test_pagina_de_login_e_tratada_como_erro(self) -> None:
        """Um corpo que não é objeto JSON (ex.: HTML) é rejeitado."""
        with patch("httpx.Client") as mock_cls:
            _mock_cliente(mock_cls, _resposta_ok("<html>login</html>"))

            with pytest.raises(AzureApiError, match="Resposta não-JSON"):
                azure_request("GET", "https://x")
