"""Cache de estado da UI (BFF_BROKER) para as respostas do Azure DevOps.

A camada de request nunca chama o Azure diretamente — só lê o cache
aqui. Quando o cache está vazio, dispara a Celery task correspondente
(ver ``apps/azure/tasks.py``) e devolve um fallback seguro na hora, sem
bloquear a requisição.
"""

import json
from typing import Any

from apps.core.cache import hash_chave
from apps.core.cache import obter_ou_marcar_para_atualizar

__all__ = [
    "chave_backlog",
    "chave_diagnostico",
    "chave_projetos",
    "obter_ou_marcar_para_atualizar",
]


def chave_backlog(
    organizacao: str,
    projeto: str,
    inicio: str | None,
    fim: str | None,
    filtros: dict[str, Any],
) -> str:
    """Chave de cache do backlog para uma combinação de filtros.

    Os filtros entram na chave por meio de um JSON com as chaves
    ordenadas, para que a mesma combinação — recebida em qualquer ordem
    de query params — sempre resolva para a mesma chave.

    Args:
        organizacao: Organização consultada no Azure DevOps.
        projeto: Nome do projeto consultado.
        inicio: Data inicial (``YYYY-MM-DD``) ou ``None``.
        fim: Data final (``YYYY-MM-DD``) ou ``None``.
        filtros: Filtros adicionais já normalizados.

    Returns:
        Chave de cache determinística para essa combinação.
    """
    assinatura = json.dumps(filtros, sort_keys=True, ensure_ascii=False)
    return "azure:backlog:" + hash_chave(
        organizacao,
        projeto,
        inicio or "",
        fim or "",
        assinatura,
    )


def chave_projetos(
    organizacao: str,
    top: int,
    skip: int,
    token_continuacao: str | None,
) -> str:
    """Chave de cache de uma página da listagem de projetos.

    Args:
        organizacao: Organização consultada no Azure DevOps.
        top: Número máximo de projetos por página.
        skip: Número de projetos pulados.
        token_continuacao: Token da página consultada, ou ``None``.

    Returns:
        Chave de cache determinística para essa página.
    """
    return "azure:projetos:" + hash_chave(
        organizacao,
        str(top),
        str(skip),
        token_continuacao or "",
    )


def chave_diagnostico(organizacao: str, projeto: str) -> str:
    """Chave de cache do diagnóstico de um projeto.

    Args:
        organizacao: Organização consultada no Azure DevOps.
        projeto: Nome do projeto consultado.

    Returns:
        Chave de cache determinística para esse projeto.
    """
    return "azure:diagnostico:" + hash_chave(organizacao, projeto)
