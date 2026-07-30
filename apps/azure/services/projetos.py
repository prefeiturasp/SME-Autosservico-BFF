"""Serviço de listagem de projetos do Azure DevOps.

Diferente do backlog, este recurso é de organização (não de projeto) e
pagina pelo token de continuação que o Azure devolve no header
``x-ms-continuationtoken``.
"""

import logging
from typing import Any

from apps.azure import client
from apps.azure.constants import CABECALHO_TOKEN_CONTINUACAO
from apps.azure.constants import PROJETOS_TOP_PADRAO
from apps.azure.constants import RECURSO_PROJETOS
from apps.azure.constants import VERSAO_API

logger = logging.getLogger("bff_azure")


def _criar_projeto(bruto: dict[str, Any]) -> dict[str, Any]:
    """Converte um projeto bruto do Azure no formato de saída.

    Args:
        bruto: Projeto como devolvido pelo Azure.

    Returns:
        Projeto no formato consumido pelo frontend.
    """
    return {
        "id": bruto.get("id", ""),
        "name": bruto.get("name", ""),
        "description": bruto.get("description"),
        "url": bruto.get("url"),
        "state": bruto.get("state"),
        "revision": bruto.get("revision"),
        "visibility": bruto.get("visibility"),
        "last_update_time": bruto.get("lastUpdateTime"),
    }


def montar_projetos_vazio() -> dict[str, Any]:
    """Monta a resposta de listagem vazia.

    Serve como fallback seguro da view em cache frio, preservando o
    contrato sem quebrar a interface.

    Returns:
        Listagem vazia no formato consumido pelo frontend.
    """
    return {
        "count": 0,
        "total_count": None,
        "projects": [],
        "continuation_token": None,
        "has_more": False,
    }


def obter_projetos(
    organizacao: str,
    top: int = PROJETOS_TOP_PADRAO,
    skip: int = 0,
    token_continuacao: str | None = None,
) -> dict[str, Any]:
    """Consulta o Azure DevOps e lista os projetos da organização.

    Args:
        organizacao: Organização no Azure DevOps.
        top: Número máximo de projetos por página.
        skip: Número de projetos a pular.
        token_continuacao: Token da próxima página, ou ``None``.

    Returns:
        Listagem paginada no formato consumido pelo frontend.
    """
    params: dict[str, Any] = {
        "api-version": VERSAO_API,
        "$top": top,
        "$skip": skip,
    }
    if token_continuacao:
        params["continuationToken"] = token_continuacao

    corpo, cabecalhos = client.azure_request_com_cabecalhos(
        "GET",
        client.montar_url(organizacao, "", RECURSO_PROJETOS),
        params=params,
    )
    proximo = cabecalhos.get(CABECALHO_TOKEN_CONTINUACAO)
    projetos = [
        _criar_projeto(bruto)
        for bruto in corpo.get("value", [])
        if isinstance(bruto, dict)
    ]

    logger.info(
        "Azure: projetos listados | org=%s count=%d has_more=%s",
        organizacao,
        len(projetos),
        proximo is not None,
    )

    return {
        "count": len(projetos),
        "total_count": corpo.get("count"),
        "projects": projetos,
        "continuation_token": proximo,
        "has_more": proximo is not None,
    }
