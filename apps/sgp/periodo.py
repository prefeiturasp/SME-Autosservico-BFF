"""Resolução do período letivo corrente do SGP.

Usado apenas pelo reaquecimento em background (Celery beat) para saber
qual (ano letivo, bimestre) manter quente no cache. O mapeamento de mês
para bimestre é aproximado — serve só para pré-aquecimento; o dado em si
é sempre calculado para o período que o frontend pedir.
"""

from datetime import date

# Mês -> bimestre letivo (aproximação para o pré-aquecimento).
_BIMESTRE_POR_MES = {
    1: 1,
    2: 1,
    3: 1,
    4: 1,
    5: 2,
    6: 2,
    7: 2,
    8: 3,
    9: 3,
    10: 4,
    11: 4,
    12: 4,
}


def periodo_corrente(hoje: date | None = None) -> tuple[int, int]:
    """Retorna ``(ano_letivo, bimestre)`` correntes de forma aproximada."""
    referencia = hoje or date.today()
    return referencia.year, _BIMESTRE_POR_MES[referencia.month]
