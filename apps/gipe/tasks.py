"""Celery tasks da integração de métricas do GIPE.

O retry de transporte já é feito dentro de ``apps.gipe.client``; a task
consulta o backend e grava o resultado na chave do ano letivo. Como no
SERAp, contrato degradado (``atualizado_em`` nulo, por falha de banco) não
é gravado: a próxima requisição tenta de novo, em vez de servir blocos
nulos até o TTL vencer.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from apps.gipe import client
from apps.gipe.constants import ano_letivo_corrente
from apps.gipe.constants import chave_cache_metricas

logger = logging.getLogger("bff_gipe")


@shared_task(name="gipe.atualizar_metricas")
def atualizar_metricas(ano_letivo: int) -> None:
    """Consulta o backend e atualiza o cache das métricas do GIPE."""
    resultado = client.obter_metricas(ano_letivo)
    if resultado.get("atualizado_em") is None:
        logger.warning(
            "GIPE: backend devolveu métricas degradadas (atualizado_em nulo) "
            "para ano_letivo=%s — cache não atualizado",
            ano_letivo,
        )
        return
    cache.set(
        chave_cache_metricas(ano_letivo),
        resultado,
        timeout=settings.GIPE_CACHE_TTL_METRICAS_SECONDS,
    )


@shared_task(name="gipe.aquecer_ano_corrente")
def aquecer_ano_corrente() -> None:
    """Mantém quente o cache do ano letivo corrente (via beat)."""
    atualizar_metricas(ano_letivo_corrente())
