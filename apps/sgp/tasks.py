"""Celery tasks da integração de métricas do SGP.

O retry de transporte já é feito em ``apps.core.client_backend``; a task
apenas consulta o backend e grava o resultado no cache. Se falhar, a
chave de cache continua ausente e a próxima requisição tenta de novo.
"""

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from apps.sgp import client
from apps.sgp import periodo
from apps.sgp.constants import chave_cache_metricas


@shared_task(name="sgp.atualizar_metricas")
def atualizar_metricas(ano_letivo: int, bimestre: int) -> None:
    """Consulta o backend e atualiza o cache das métricas do SGP."""
    resultado = client.obter_metricas(ano_letivo, bimestre)
    cache.set(
        chave_cache_metricas(ano_letivo, bimestre),
        resultado,
        timeout=settings.SGP_CACHE_TTL_METRICAS_SECONDS,
    )


@shared_task(name="sgp.aquecer_periodo_corrente")
def aquecer_periodo_corrente() -> None:
    """Mantém quente o cache do período letivo corrente (via beat)."""
    ano_letivo, bimestre = periodo.periodo_corrente()
    atualizar_metricas(ano_letivo, bimestre)
