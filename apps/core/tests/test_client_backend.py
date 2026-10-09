"""Testes do cliente HTTP compartilhado do backend."""

from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from apps.core.client_backend import BackendMetricasError
from apps.core.client_backend import obter_json


def _mock_cliente(mock_cls: MagicMock, resposta: MagicMock) -> MagicMock:
    """Configura ``httpx.Client`` mockado como context manager."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = resposta
    mock_cls.return_value = mock_client
    return mock_client


def _resposta_ok(corpo: object) -> MagicMock:
    """Monta uma resposta HTTP bem-sucedida com o corpo informado."""
    resposta = MagicMock(spec=httpx.Response)
    resposta.raise_for_status.return_value = None
    resposta.json.return_value = corpo
    return resposta


def _resposta_erro(status_code: int) -> MagicMock:
    """Monta uma resposta HTTP cujo ``raise_for_status`` falha."""
    resposta = MagicMock(spec=httpx.Response)
    resposta.raise_for_status.side_effect = httpx.HTTPStatusError(
        str(status_code),
        request=MagicMock(),
        response=MagicMock(status_code=status_code),
    )
    return resposta


class TestObterJson:
    """Testes cobrindo obter_json()."""

    def test_monta_url_cabecalho_e_parametros(self, settings) -> None:
        """Chama o backend com URL, API Key e query string corretas."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend/"
        settings.AUTOSSERVICO_BACKEND_API_KEY = "chave"
        settings.API_KEY_HEADER = "X-Api-Key"
        contrato: dict[str, Any] = {"atualizado_em": None}

        with patch("apps.core.client_backend.httpx.Client") as mock_cls:
            cliente = _mock_cliente(mock_cls, _resposta_ok(contrato))
            resultado = obter_json("/api/v1/rota/", {"a": 1})

        assert resultado == contrato
        cliente.get.assert_called_once_with(
            "https://backend/api/v1/rota/",
            headers={"X-Api-Key": "chave"},
            params={"a": 1},
        )

    @patch("apps.core.client_backend.httpx.Client")
    def test_resposta_nao_json_levanta_erro(
        self, mock_cls: MagicMock, settings
    ) -> None:
        """Um corpo que não é objeto JSON levanta BackendMetricasError."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        _mock_cliente(mock_cls, _resposta_ok(["lista"]))

        with pytest.raises(BackendMetricasError):
            obter_json("/rota/")

    def test_retenta_erro_transitorio(self, settings) -> None:
        """Uma falha de conexão é retentada até obter sucesso."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        resposta = _resposta_ok({"ok": True})

        with (
            patch("apps.core.client_backend.time.sleep"),
            patch("apps.core.client_backend.httpx.Client") as mock_cls,
        ):
            cliente = _mock_cliente(mock_cls, resposta)
            cliente.get.side_effect = [httpx.ConnectError("down"), resposta]
            resultado = obter_json("/rota/")

        assert resultado == {"ok": True}
        assert cliente.get.call_count == 2

    def test_retenta_status_retriavel_e_esgota(self, settings) -> None:
        """Um 503 é retentado até esgotar as tentativas e então propaga."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"

        with (
            patch("apps.core.client_backend.time.sleep"),
            patch("apps.core.client_backend.httpx.Client") as mock_cls,
        ):
            cliente = _mock_cliente(mock_cls, _resposta_erro(503))
            with pytest.raises(httpx.HTTPStatusError):
                obter_json("/rota/")

        assert cliente.get.call_count == 5

    @patch("apps.core.client_backend.httpx.Client")
    def test_erro_http_nao_retriavel_propaga_sem_repetir(
        self, mock_cls: MagicMock, settings
    ) -> None:
        """Um 404 não é retentado e propaga o erro."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        cliente = _mock_cliente(mock_cls, _resposta_erro(404))

        with pytest.raises(httpx.HTTPStatusError):
            obter_json("/rota/")

        assert cliente.get.call_count == 1
