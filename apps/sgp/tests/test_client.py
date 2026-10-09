"""Testes do cliente de métricas do SGP."""

from unittest.mock import patch

from apps.sgp.client import obter_metricas
from apps.sgp.constants import CAMINHO_METRICAS


class TestObterMetricas:
    """Testes cobrindo obter_metricas()."""

    def test_envia_ano_letivo_e_bimestre(self) -> None:
        """Repassa o período ao backend e devolve o contrato."""
        with patch(
            "apps.core.client_backend.obter_json", return_value={"ok": 1}
        ) as mock_obter:
            resultado = obter_metricas(2026, 2)

        assert resultado == {"ok": 1}
        mock_obter.assert_called_once_with(
            CAMINHO_METRICAS, {"ano_letivo": 2026, "bimestre": 2}
        )
