"""Contrato de fallback das métricas do Bens Físicos.

Usado pela view quando o cache está frio: devolve os blocos nulos, sem
nenhuma chamada de rede.
"""

from typing import Any


def metricas_indisponivel() -> dict[str, Any]:
    """Monta o contrato de métricas com os blocos nulos."""
    return {
        "atualizado_em": None,
        "usuarios": None,
        "cadastro_de_bens": None,
        "baixas_fisicas": None,
        "movimentacoes": None,
    }
