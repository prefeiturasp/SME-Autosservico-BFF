"""Testes do cliente HTTP de métricas do Bens Físicos."""

from unittest.mock import MagicMock
from unittest.mock import patch

import httpx

from apps.bensfisicos.client import obter_metricas


class TestObterMetricas:
    """Testes cobrindo obter_metricas()."""

    def test_chama_o_caminho_do_bens_fisicos(self, settings) -> None:
        """Chama o endpoint do backend com a API Key e sem parâmetros."""
        settings.AUTOSSERVICO_BACKEND_URL = "https://backend"
        settings.AUTOSSERVICO_BACKEND_API_KEY = "chave"
        resposta = MagicMock(spec=httpx.Response)
        resposta.json.return_value = {"atualizado_em": None}

        with patch("apps.core.client_backend.httpx.Client") as mock_cls:
            cliente = MagicMock()
            cliente.__enter__ = MagicMock(return_value=cliente)
            cliente.__exit__ = MagicMock(return_value=False)
            cliente.get.return_value = resposta
            mock_cls.return_value = cliente
            resultado = obter_metricas()

        assert resultado == {"atualizado_em": None}
        cliente.get.assert_called_once_with(
            "https://backend/api/v1/bens-fisicos/metricas/",
            headers={settings.API_KEY_HEADER: "chave"},
            params=None,
        )
