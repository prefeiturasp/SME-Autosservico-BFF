"""Serviço de diagnóstico do backlog do Azure DevOps.

Endpoint de apoio: busca o backlog do projeto **sem nenhum filtro de
tipo** e reporta quantos work items existem de cada
``System.WorkItemType``, com uma amostra dos primeiros itens. Serve
para descobrir quais tipos um projeto realmente usa antes de configurar
os filtros do dashboard.
"""

import logging
from typing import Any

from apps.azure.constants import DIAGNOSTICO_TAMANHO_AMOSTRA
from apps.azure.constants import DIAGNOSTICO_TAMANHO_TITULO
from apps.azure.constants import DIAGNOSTICO_TIPO_DESCONHECIDO
from apps.azure.services import backlog as servico_backlog

logger = logging.getLogger("bff_azure")


def montar_diagnostico(
    projeto: str, backlog: dict[str, Any]
) -> dict[str, Any]:
    """Deriva a contagem por tipo e a amostra a partir de um backlog.

    Função pura: não faz nenhuma chamada de rede.

    Args:
        projeto: Nome do projeto consultado.
        backlog: Backlog já montado por ``services.backlog``.

    Returns:
        Diagnóstico no formato consumido pelo frontend.
    """
    itens = [*backlog["parents"], *backlog["children"]]

    contagens: dict[str, int] = {}
    for item in itens:
        tipo = item.get("work_item_type") or DIAGNOSTICO_TIPO_DESCONHECIDO
        contagens[tipo] = contagens.get(tipo, 0) + 1

    return {
        "project_name": projeto,
        "total_items": backlog["total_items"],
        "work_item_type_counts": contagens,
        "sample_items": [
            {
                "id": item["id"],
                "title": (item.get("title") or "")[
                    :DIAGNOSTICO_TAMANHO_TITULO
                ],
                "type": item.get("work_item_type"),
                "state": item.get("state"),
            }
            for item in itens[:DIAGNOSTICO_TAMANHO_AMOSTRA]
        ],
    }


def montar_diagnostico_vazio(projeto: str) -> dict[str, Any]:
    """Monta o diagnóstico vazio.

    Serve como fallback seguro da view em cache frio.

    Args:
        projeto: Nome do projeto consultado.

    Returns:
        Diagnóstico vazio no formato consumido pelo frontend.
    """
    return {
        "project_name": projeto,
        "total_items": 0,
        "work_item_type_counts": {},
        "sample_items": [],
    }


def obter_diagnostico(organizacao: str, projeto: str) -> dict[str, Any]:
    """Consulta o Azure DevOps e monta o diagnóstico de um projeto.

    Args:
        organizacao: Organização no Azure DevOps.
        projeto: Nome do projeto consultado.

    Returns:
        Diagnóstico no formato consumido pelo frontend.
    """
    backlog = servico_backlog.obter_backlog(
        organizacao, projeto, None, None, None
    )
    diagnostico = montar_diagnostico(projeto, backlog)

    logger.info(
        "Azure: diagnóstico montado | org=%s projeto=%s tipos=%d",
        organizacao,
        projeto,
        len(diagnostico["work_item_type_counts"]),
    )

    return diagnostico
