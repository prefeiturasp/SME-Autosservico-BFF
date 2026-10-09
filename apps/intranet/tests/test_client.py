"""Testes do cliente de métricas do Intranet."""

from unittest.mock import patch

from apps.intranet.client import obter_metricas
from apps.intranet.constants import CAMINHO_METRICAS


class TestObterMetricas:
    """Testes cobrindo obter_metricas()."""

    def test_sem_mes_envia_so_o_periodo(self) -> None:
        """Sem ``mes``, só o ``periodo`` vai na query string."""
        with patch(
            "apps.core.client_backend.obter_json", return_value={"ok": 1}
        ) as mock_obter:
            resultado = obter_metricas("geral", None)

        assert resultado == {"ok": 1}
        mock_obter.assert_called_once_with(
            CAMINHO_METRICAS, {"periodo": "geral"}
        )

    def test_envia_mes_quando_informado(self) -> None:
        """Com ``mes`` informado, ele é repassado ao backend."""
        with patch("apps.core.client_backend.obter_json") as mock_obter:
            obter_metricas("mes", "2026-09")

        mock_obter.assert_called_once_with(
            CAMINHO_METRICAS, {"periodo": "mes", "mes": "2026-09"}
        )
