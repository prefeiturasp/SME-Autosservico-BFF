"""Contrato de fallback das métricas do SERAp.

Usado pela view quando o cache está frio (a task de atualização acabou de
ser disparada em background) — devolve o contrato com todos os blocos
nulos, sem nenhuma chamada de rede.
"""

from typing import Any


def metricas_indisponivel(ano: int, bimestre: int) -> dict[str, Any]:
    """Monta o contrato de métricas com todos os blocos nulos."""
    return {
        "atualizado_em": None,
        "ano": ano,
        "bimestre": bimestre,
        "usuarios": None,
        "provas": None,
    }
