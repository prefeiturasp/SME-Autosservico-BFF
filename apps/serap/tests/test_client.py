"""Testes do cliente HTTP de métricas do SERAp."""

from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from apps.serap.client import BackendMetricasError
from apps.serap.client import obter_metricas


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

    def test_retorna_o_contrato_e_envia_ano_e_bimestre(self, settings) -> None:
        """Chama o backend com ano/bimestre e devolve o JSON de objeto."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        settings.AUTOSSERVICO_BACKEND_API_KEY = "chave"
        contrato: dict[str, Any] = {"atualizado_em": None, "provas": {}}

        with patch("apps.serap.client.httpx.Client") as mock_cls:
            cliente = _mock_cliente(mock_cls, _resposta_ok(contrato))
            resultado = obter_metricas(2026, 2)

        assert resultado == contrato
        cliente.get.assert_called_once_with(
            "https://backend/api/v1/serap/provas/metricas/",
            headers={settings.API_KEY_HEADER: "chave"},
            params={"ano": 2026, "bimestre": 2},
        )

    @patch("apps.serap.client.httpx.Client")
    def test_resposta_nao_json_levanta_erro(
        self, mock_cls: MagicMock, settings
    ) -> None:
        """Um corpo que não é objeto JSON levanta BackendMetricasError."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        _mock_cliente(mock_cls, _resposta_ok(["lista"]))

        with pytest.raises(BackendMetricasError):
            obter_metricas(2026, 2)

    def test_retenta_erro_transitorio(self, settings) -> None:
        """Uma falha de conexão é retentada até obter sucesso."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        resposta = _resposta_ok({"ok": True})

        with (
            patch("apps.serap.client.time.sleep"),
            patch("apps.serap.client.httpx.Client") as mock_cls,
        ):
            cliente = _mock_cliente(mock_cls, resposta)
            cliente.get.side_effect = [httpx.ConnectError("down"), resposta]
            resultado = obter_metricas(2026, 2)

        assert resultado == {"ok": True}
        assert cliente.get.call_count == 2

    def test_retenta_status_retriavel_e_esgota(self, settings) -> None:
        """Um 503 é retentado até esgotar as tentativas e então propaga."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503",
            request=MagicMock(),
            response=MagicMock(status_code=503),
        )

        with (
            patch("apps.serap.client.time.sleep"),
            patch("apps.serap.client.httpx.Client") as mock_cls,
        ):
            cliente = _mock_cliente(mock_cls, resposta)
            with pytest.raises(httpx.HTTPStatusError):
                obter_metricas(2026, 2)

        assert cliente.get.call_count == 5

    @patch("apps.serap.client.httpx.Client")
    def test_erro_http_nao_retriavel_propaga_sem_repetir(
        self, mock_cls: MagicMock, settings
    ) -> None:
        """Um 404 não é retentado e propaga o erro."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        cliente = _mock_cliente(mock_cls, resposta)

        with pytest.raises(httpx.HTTPStatusError):
            obter_metricas(2026, 2)

        assert cliente.get.call_count == 1
