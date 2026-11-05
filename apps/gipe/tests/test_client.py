"""Testes do cliente HTTP de métricas do GIPE."""

from unittest.mock import MagicMock
from unittest.mock import patch

import httpx

from apps.gipe.client import obter_metricas


def _mock_cliente(mock_cls: MagicMock, resposta: MagicMock) -> MagicMock:
    """Configura ``httpx.Client`` mockado como context manager."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = resposta
    mock_cls.return_value = mock_client
    return mock_client


class TestObterMetricas:
    """Testes cobrindo obter_metricas()."""

    def test_envia_o_ano_letivo_como_query_string(self, settings) -> None:
        """Chama o caminho do GIPE com o ano letivo recebido."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        settings.AUTOSSERVICO_BACKEND_API_KEY = "chave"
        resposta = MagicMock(spec=httpx.Response)
        resposta.json.return_value = {"atualizado_em": None}

        with patch("apps.core.client_backend.httpx.Client") as mock_cls:
            cliente = _mock_cliente(mock_cls, resposta)
            resultado = obter_metricas(2026)

        assert resultado == {"atualizado_em": None}
        cliente.get.assert_called_once_with(
            "https://backend/api/v1/gipe/metricas/",
            headers={settings.API_KEY_HEADER: "chave"},
            params={"ano_letivo": 2026},
        )
