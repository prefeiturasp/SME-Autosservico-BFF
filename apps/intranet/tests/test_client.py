"""Testes do cliente de métricas do Intranet."""

from unittest.mock import patch

from apps.intranet.client import obter_metricas


class TestObterMetricas:
    """Testes cobrindo obter_metricas()."""

    def test_sem_mes_envia_so_o_periodo(self) -> None:
        """Sem ``mes``, só o ``periodo`` vai na query string."""
        with patch(
            "apps.core.client_backend.obter_metricas", return_value={"ok": 1}
        ) as mock_obter:
            resultado = obter_metricas("geral", None)

        assert resultado == {"ok": 1}
        assert mock_obter.call_args.args == ("/api/v1/intranet/metricas/",)
        assert mock_obter.call_args.kwargs["rotulo"] == "Intranet"
        assert mock_obter.call_args.kwargs["parametros"] == {
            "periodo": "geral"
        }

    def test_envia_mes_quando_informado(self) -> None:
        """Com ``mes`` informado, ele é repassado ao backend."""
        with patch("apps.core.client_backend.obter_metricas") as mock_obter:
            obter_metricas("mes", "2026-09")

        assert mock_obter.call_args.kwargs["parametros"] == {
            "periodo": "mes",
            "mes": "2026-09",
        }
