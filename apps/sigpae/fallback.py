"""Contrato de fallback das métricas do SIGPAE.

Usado pela view quando o cache está frio (a task de atualização acabou
de ser disparada em background) — devolve o contrato com todos os
indicadores nulos, sem nenhuma chamada de rede.
"""

from typing import Any


def metricas_indisponivel() -> dict[str, Any]:
    """Monta o contrato de métricas com todos os indicadores nulos."""
    return {
        "atualizado_em": None,
        "usuarios": {
            "com_acesso_ativo": None,
            "unicos_por_dia": None,
            "acessos_hoje": None,
            "por_tipo_perfil": {
                "codae": None,
                "dre": None,
                "ue": None,
                "empresa": None,
            },
            "comparativo_acessos": None,
        },
        "alimentacao_terceirizada": {
            "medicoes_iniciais": {
                "aguardando_envio_ue": None,
                "enviadas_pelas_unidades": None,
                "aprovadas_pelas_dres": None,
                "aguardando_codae": None,
                "aprovadas_codae": None,
            },
        },
    }
