"""Testes do cliente HTTP de métricas do SIGPAE."""

from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from apps.sigpae.client import BackendMetricasError
from apps.sigpae.client import obter_metricas


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


class TestObterMetricas:
    """Testes cobrindo obter_metricas()."""

    def test_retorna_o_contrato(self, settings) -> None:
        """Uma resposta JSON de objeto é devolvida como dicionário."""
        settings.AUTOSSERVICO_BACKEND_URL = "http://backend"
        settings.AUTOSSERVICO_BACKEND_API_KEY = "chave"
        contrato: dict[str, Any] = {"atualizado_em": None, "usuarios": {}}

        with patch("apps.sigpae.client.httpx.Client") as mock_cls:
            _mock_cliente(mock_cls, _resposta_ok(contrato))
            resultado = obter_metricas()

        assert resultado == contrato

    @patch("apps.sigpae.client.httpx.Client")
    def test_resposta_nao_json_levanta_erro(
        self, mock_cls: MagicMock, settings
    ) -> None:
        """Um corpo que não é objeto JSON levanta BackendMetricasError."""
        settings.AUTOSSERVICO_BACKEND_URL = "http://backend"
        _mock_cliente(mock_cls, _resposta_ok(["lista"]))

        with pytest.raises(BackendMetricasError):
            obter_metricas()

    def test_retenta_erro_transitorio(self, settings) -> None:
        """Uma falha de conexão é retentada até obter sucesso."""
        settings.AUTOSSERVICO_BACKEND_URL = "http://backend"
        resposta = _resposta_ok({"ok": True})

        with (
            patch("apps.sigpae.client.time.sleep"),
            patch("apps.sigpae.client.httpx.Client") as mock_cls,
        ):
            cliente = _mock_cliente(mock_cls, resposta)
            cliente.get.side_effect = [httpx.ConnectError("down"), resposta]
            resultado = obter_metricas()

        assert resultado == {"ok": True}
        assert cliente.get.call_count == 2

    @patch("apps.sigpae.client.httpx.Client")
    def test_erro_http_nao_retriavel_propaga_sem_repetir(
        self, mock_cls: MagicMock, settings
    ) -> None:
        """Um 404 não é retentado e propaga o erro."""
        settings.AUTOSSERVICO_BACKEND_URL = "http://backend"
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        cliente = _mock_cliente(mock_cls, resposta)

        with pytest.raises(httpx.HTTPStatusError):
            obter_metricas()

        assert cliente.get.call_count == 1
