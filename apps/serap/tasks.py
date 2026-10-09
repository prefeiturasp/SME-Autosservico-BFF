"""Celery tasks da integração de métricas do SERAp.

O retry de transporte já é feito dentro de ``apps.serap.client``; a task
apenas consulta o backend e grava o resultado no cache. Se falhar, ou se o
backend responder degradado (``atualizado_em`` nulo, por falha de banco), a
chave de cache continua ausente e a próxima requisição tenta de novo.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from apps.serap import client
from apps.serap.constants import chave_cache_metricas
from apps.sgp import periodo

logger = logging.getLogger("bff_serap")


@shared_task(name="serap.atualizar_metricas")
def atualizar_metricas(ano: int, bimestre: int) -> None:
    """Consulta o backend e atualiza o cache das métricas do SERAp."""
    resultado = client.obter_metricas(ano, bimestre)
    if resultado.get("atualizado_em") is None:
        logger.warning(
            "SERAp: backend devolveu métricas degradadas (atualizado_em nulo) "
            "para ano=%s bimestre=%s — cache não atualizado",
            ano,
            bimestre,
        )
        return
    cache.set(
        chave_cache_metricas(ano, bimestre),
        resultado,
        timeout=settings.SERAP_CACHE_TTL_METRICAS_SECONDS,
    )


@shared_task(name="serap.aquecer_periodo_corrente")
def aquecer_periodo_corrente() -> None:
    """Mantém quente o cache do período corrente (via beat).

    Reaproveita o mapeamento mês -> bimestre do SGP: o calendário escolar
    é o mesmo da rede.
    """
    ano, bimestre = periodo.periodo_corrente()
    atualizar_metricas(ano, bimestre)
