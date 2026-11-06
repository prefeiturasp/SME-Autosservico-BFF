"""Celery tasks da integração de métricas do SGP.

O retry de transporte já é feito dentro de ``apps.sgp.client``; a task
apenas consulta o backend e grava o resultado no cache. Se falhar, a
chave de cache continua ausente e a próxima requisição tenta de novo.
"""

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from apps.sgp import client
from apps.sgp import periodo
from apps.sgp.constants import CHAVE_CACHE_PERIODOS
from apps.sgp.constants import SEGMENTO_FUNDAMENTAL_MEDIO
from apps.sgp.constants import chave_cache_metricas


@shared_task(name="sgp.atualizar_metricas")
def atualizar_metricas(
    ano_letivo: int,
    segmento: str,
    semestre: int | None,
    bimestre: int,
) -> None:
    """Consulta o backend e atualiza o cache das métricas do SGP."""
    resultado = client.obter_metricas(ano_letivo, segmento, semestre, bimestre)
    cache.set(
        chave_cache_metricas(ano_letivo, segmento, semestre, bimestre),
        resultado,
        timeout=settings.SGP_CACHE_TTL_METRICAS_SECONDS,
    )


@shared_task(name="sgp.atualizar_periodos")
def atualizar_periodos() -> None:
    """Consulta o backend e atualiza o cache das opções de período."""
    cache.set(
        CHAVE_CACHE_PERIODOS,
        client.obter_periodos(),
        timeout=settings.SGP_CACHE_TTL_PERIODOS_SECONDS,
    )


@shared_task(name="sgp.aquecer_periodo_corrente")
def aquecer_periodo_corrente() -> None:
    """Mantém quente o cache do bimestre corrente (via beat).

    Só Fundamental/Médio, que é o padrão do painel. A EJA vai sob demanda.
    """
    ano_letivo, bimestre = periodo.periodo_corrente()
    atualizar_metricas(ano_letivo, SEGMENTO_FUNDAMENTAL_MEDIO, None, bimestre)
