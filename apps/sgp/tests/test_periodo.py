"""Testes da resolução do período letivo corrente do SGP."""

from datetime import date

import pytest

from apps.sgp.periodo import periodo_corrente


@pytest.mark.parametrize(
    ("mes", "bimestre_esperado"),
    [(1, 1), (4, 1), (5, 2), (7, 2), (8, 3), (9, 3), (10, 4), (12, 4)],
)
def test_mapeia_mes_para_bimestre(mes: int, bimestre_esperado: int) -> None:
    """Cada mês cai no bimestre letivo aproximado esperado."""
    ano, bimestre = periodo_corrente(date(2026, mes, 15))

    assert ano == 2026
    assert bimestre == bimestre_esperado


def test_usa_a_data_de_hoje_por_padrao() -> None:
    """Sem argumento, resolve o ano corrente."""
    ano, bimestre = periodo_corrente()

    assert ano == date.today().year
    assert 1 <= bimestre <= 4
