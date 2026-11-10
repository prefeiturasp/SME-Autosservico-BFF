"""Celery tasks da integração de métricas do Bens Físicos.

Contrato degradado (``atualizado_em`` nulo, por falha de banco) não é
gravado: a próxima requisição tenta de novo, em vez de servir blocos
nulos até o TTL vencer.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from apps.bensfisicos import client
from apps.bensfisicos.constants import CHAVE_CACHE_METRICAS

logger = logging.getLogger("bff_bensfisicos")


@shared_task(name="bensfisicos.atualizar_metricas")
def atualizar_metricas() -> None:
    """Consulta o backend e atualiza o cache das métricas do Bens Físicos."""
    resultado = client.obter_metricas()
    if resultado.get("atualizado_em") is None:
        logger.warning(
            "Bens Físicos: backend devolveu métricas degradadas "
            "(atualizado_em nulo) — cache não atualizado"
        )
        return
    cache.set(
        CHAVE_CACHE_METRICAS,
        resultado,
        timeout=settings.BENS_FISICOS_CACHE_TTL_METRICAS_SECONDS,
    )
