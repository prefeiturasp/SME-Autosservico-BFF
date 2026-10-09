"""Contrato de fallback das métricas do SIG-Escola.

Usado pela view quando o cache está frio (a task de atualização acabou de
ser disparada em background) — devolve o contrato com os blocos nulos e
os filtros pedidos, sem nenhuma chamada de rede.
"""

from collections.abc import Mapping
from typing import Any

from apps.sigescola.constants import FILTROS


def metricas_indisponivel(filtros: Mapping[str, str]) -> dict[str, Any]:
    """Monta o contrato de métricas com os blocos nulos."""
    return {
        "atualizado_em": None,
        "filtros": {nome: filtros.get(nome) for nome in FILTROS},
        "opcoes": None,
        "usuarios": None,
        "plano_anual_de_atividades": None,
        "prestacao_de_contas": None,
        "situacao_patrimonial": None,
    }
