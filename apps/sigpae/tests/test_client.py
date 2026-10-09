"""Testes do cliente de métricas do SIGPAE."""

from unittest.mock import patch

from apps.sigpae.client import obter_metricas
from apps.sigpae.constants import CAMINHO_METRICAS


class TestObterMetricas:
    """Testes cobrindo obter_metricas()."""

    def test_chama_a_rota_do_sigpae(self) -> None:
        """Chama a rota de métricas do SIGPAE e devolve o contrato."""
        with patch(
            "apps.core.client_backend.obter_json", return_value={"ok": 1}
        ) as mock_obter:
            resultado = obter_metricas()

        assert resultado == {"ok": 1}
        mock_obter.assert_called_once_with(CAMINHO_METRICAS)
