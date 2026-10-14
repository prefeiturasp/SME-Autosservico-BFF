"""Celery tasks da integração com o Azure DevOps.

Nenhuma task usa retry próprio (``bind=True``/``self.retry``) — o retry
de transporte já é feito inteiramente dentro de ``apps.azure.client``.
Se uma task falhar (ex.: Azure indisponível além do orçamento de retry
do client), ela só falha e loga; a chave de cache correspondente
continua ausente/expirada, e a próxima requisição tenta de novo
naturalmente.
"""

from typing import Any

from celery import shared_task
from django.core.cache import cache

from apps.azure import cache as azure_cache
from apps.azure.constants import LIMITE_TEMPO_TASK_SEGUNDOS
from apps.azure.constants import TTL_CACHE_BACKLOG_SEGUNDOS
from apps.azure.constants import TTL_CACHE_DIAGNOSTICO_SEGUNDOS
from apps.azure.constants import TTL_CACHE_PROJETOS_SEGUNDOS
from apps.azure.services import backlog as servico_backlog
from apps.azure.services import diagnostico as servico_diagnostico
from apps.azure.services import projetos as servico_projetos


@shared_task(
    name="azure.atualizar_backlog",
    time_limit=LIMITE_TEMPO_TASK_SEGUNDOS,
)
def atualizar_backlog(
    organizacao: str,
    projeto: str,
    inicio: str | None,
    fim: str | None,
    filtros: dict[str, Any],
) -> None:
    """Consulta o Azure DevOps e atualiza o cache do backlog.

    Usa ``AZURE_TASK_TIME_LIMIT`` no lugar do ``CELERY_TASK_TIME_LIMIT``
    global: o backlog é paginado em lotes de 200 ids e uma carga grande
    passa com folga dos 30s dimensionados para o Zabbix.

    Args:
        organizacao: Organização no Azure DevOps.
        projeto: Nome do projeto consultado.
        inicio: Data inicial (``YYYY-MM-DD``) ou ``None``.
        fim: Data final (``YYYY-MM-DD``) ou ``None``.
        filtros: Filtros adicionais já normalizados.
    """
    resultado = servico_backlog.obter_backlog(
        organizacao, projeto, inicio, fim, filtros
    )
    chave = azure_cache.chave_backlog(
        organizacao, projeto, inicio, fim, filtros
    )
    cache.set(
        chave,
        resultado,
        timeout=TTL_CACHE_BACKLOG_SEGUNDOS,
    )


@shared_task(
    name="azure.atualizar_projetos",
    time_limit=LIMITE_TEMPO_TASK_SEGUNDOS,
)
def atualizar_projetos(
    organizacao: str,
    top: int,
    skip: int,
    token_continuacao: str | None,
) -> None:
    """Consulta o Azure DevOps e atualiza o cache da lista de projetos.

    Args:
        organizacao: Organização no Azure DevOps.
        top: Número máximo de projetos por página.
        skip: Número de projetos a pular.
        token_continuacao: Token da próxima página, ou ``None``.
    """
    resultado = servico_projetos.obter_projetos(
        organizacao, top, skip, token_continuacao
    )
    chave = azure_cache.chave_projetos(
        organizacao, top, skip, token_continuacao
    )
    cache.set(
        chave,
        resultado,
        timeout=TTL_CACHE_PROJETOS_SEGUNDOS,
    )


@shared_task(
    name="azure.atualizar_diagnostico",
    time_limit=LIMITE_TEMPO_TASK_SEGUNDOS,
)
def atualizar_diagnostico(organizacao: str, projeto: str) -> None:
    """Consulta o Azure DevOps e atualiza o cache do diagnóstico.

    Args:
        organizacao: Organização no Azure DevOps.
        projeto: Nome do projeto consultado.
    """
    resultado = servico_diagnostico.obter_diagnostico(organizacao, projeto)
    chave = azure_cache.chave_diagnostico(organizacao, projeto)
    cache.set(
        chave,
        resultado,
        timeout=TTL_CACHE_DIAGNOSTICO_SEGUNDOS,
    )
