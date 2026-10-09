"""Resposta da view enquanto o cache das métricas está frio."""

from typing import Any


def metricas_indisponivel(periodo: str, mes: str | None) -> dict[str, Any]:
    """Monta o contrato de métricas com todos os blocos nulos."""
    return {
        "atualizado_em": None,
        "periodo": periodo,
        "mes": mes,
        "kpis": None,
        "sorteios": None,
        "ordem_inscricao": None,
        "oportunidades": None,
    }
