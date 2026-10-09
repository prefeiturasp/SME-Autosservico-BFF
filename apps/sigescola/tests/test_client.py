"""Testes do cliente HTTP de métricas do SIG-Escola."""

from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import pytest

from apps.sigescola.client import obter_metricas


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

    def test_envia_os_filtros_como_query_string(self, settings) -> None:
        """Chama o caminho do SIG-Escola com os filtros recebidos."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        settings.AUTOSSERVICO_BACKEND_API_KEY = "chave"
        resposta = MagicMock(spec=httpx.Response)
        resposta.json.return_value = {"atualizado_em": None}

        with patch("apps.core.client_backend.httpx.Client") as mock_cls:
            cliente = _mock_cliente(mock_cls, resposta)
            resultado = obter_metricas({"periodo": "2026.2", "dre": "108100"})

        assert resultado == {"atualizado_em": None}
        cliente.get.assert_called_once_with(
            "https://backend/api/v1/sigescola/metricas/",
            headers={settings.API_KEY_HEADER: "chave"},
            params={"periodo": "2026.2", "dre": "108100"},
        )

    @patch("apps.core.client_backend.httpx.Client")
    def test_periodo_inexistente_nao_e_retentado(
        self, mock_cls: MagicMock, settings
    ) -> None:
        """O 400 do backend (período que não existe) propaga sem repetir."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        resposta = MagicMock(spec=httpx.Response)
        resposta.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400",
            request=MagicMock(),
            response=MagicMock(status_code=400),
        )
        cliente = _mock_cliente(mock_cls, resposta)

        with pytest.raises(httpx.HTTPStatusError):
            obter_metricas({"periodo": "1999.9"})

        assert cliente.get.call_count == 1
