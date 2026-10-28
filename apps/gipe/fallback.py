"""Contrato de fallback das métricas do GIPE.

Usado pela view quando o cache está frio (a task de atualização acabou de
ser disparada em background) — devolve o contrato com os blocos nulos e
o ano letivo pedido, sem nenhuma chamada de rede.
"""

from typing import Any


def metricas_indisponivel(ano_letivo: int) -> dict[str, Any]:
    """Monta o contrato de métricas com os blocos nulos."""
    return {
        "atualizado_em": None,
        "ano_letivo": ano_letivo,
        "kpis": None,
        "ocorrencias": None,
        "usuarios": None,
        "produtividade": None,
    }
