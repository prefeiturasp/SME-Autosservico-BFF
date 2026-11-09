"""Contratos de fallback das métricas do SGP.

Usados com o cache frio, enquanto a task atualiza em background.
"""

from typing import Any


def metricas_indisponivel(
    ano_letivo: int, segmento: str, semestre: int | None, bimestre: int
) -> dict[str, Any]:
    """Monta o contrato de métricas com todos os blocos nulos."""
    return {
        "atualizado_em": None,
        "ano_letivo": ano_letivo,
        "bimestre": bimestre,
        "periodo": {
            "ano_letivo": ano_letivo,
            "segmento": segmento,
            "semestre": semestre,
            "bimestre": bimestre,
        },
        "usuarios": None,
        "frequencias": None,
        "sondagens": None,
        "fechamento": None,
        "conselho_classe": None,
    }


def periodos_indisponivel() -> dict[str, Any]:
    """Monta o contrato de períodos com a lista nula."""
    return {"periodos": None}
