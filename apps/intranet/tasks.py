"""Celery tasks das métricas do Intranet."""

import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from apps.intranet import client
from apps.intranet.constants import PERIODOS
from apps.intranet.constants import chave_cache_metricas

logger = logging.getLogger("bff_intranet")


@shared_task(name="intranet.atualizar_metricas")
def atualizar_metricas(periodo: str, mes: str | None) -> None:
    """Busca as métricas no backend e grava no cache.

    Se o backend falhar ao ler o banco, ele devolve tudo nulo (inclusive
    ``atualizado_em``). Nesse caso não gravamos, para tentar de novo na
    próxima requisição.
    """
    resultado = client.obter_metricas(periodo, mes)
    if resultado.get("atualizado_em") is None:
        logger.warning(
            "Intranet: backend sem dados (periodo=%s, mes=%s) — "
            "cache não atualizado",
            periodo,
            mes,
        )
        return
    cache.set(
        chave_cache_metricas(periodo, mes),
        resultado,
        timeout=settings.INTRANET_CACHE_TTL_METRICAS_SECONDS,
    )


@shared_task(name="intranet.aquecer_periodos")
def aquecer_periodos() -> None:
    """Atualiza o cache de cada período sem filtro de mês (beat).

    Uma task por período, para cada uma ter seu próprio time limit.
    """
    for periodo in PERIODOS:
        atualizar_metricas.delay(periodo, None)
