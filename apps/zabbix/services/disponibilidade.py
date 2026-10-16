"""Serviço de disponibilidade dos ambientes por sistema.

Expõe o registro estático ``DISPONIBILIDADE_FRONTEND_POR_SISTEMA`` no
formato de lista consumido pela API — nenhuma chamada de rede.
"""

from apps.zabbix.constants import DISPONIBILIDADE_FRONTEND_POR_SISTEMA


def listar_sistemas() -> list[dict[str, str]]:
    """Lista os sistemas com suas descrições de disponibilidade.

    Returns:
        Lista de dicionários com ``sistema``, ``producao`` e, quando há
        monitoramento de homologação, ``homologacao`` (ausente caso
        contrário).
    """
    sistemas: list[dict[str, str]] = []
    for nome, descricoes in DISPONIBILIDADE_FRONTEND_POR_SISTEMA.items():
        item: dict[str, str] = {
            "sistema": nome,
            "producao": descricoes.producao,
        }
        if descricoes.homologacao is not None:
            item["homologacao"] = descricoes.homologacao
        sistemas.append(item)
    return sistemas
