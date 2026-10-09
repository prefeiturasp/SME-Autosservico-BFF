"""Celery tasks da integração de métricas do SIGPAE.

O retry de transporte já é feito dentro de ``apps.sigpae.client``; a task
apenas consulta o backend e grava o resultado no cache. Se falhar, a
chave de cache continua ausente e a próxima requisição tenta de novo.
"""

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from apps.sigpae import client
from apps.sigpae.constants import CHAVE_CACHE_METRICAS


@shared_task(name="sigpae.atualizar_metricas")
def atualizar_metricas() -> None:
    """Consulta o backend e atualiza o cache das métricas do SIGPAE."""
    resultado = client.obter_metricas()
    cache.set(
        CHAVE_CACHE_METRICAS,
        resultado,
        timeout=settings.SIGPAE_CACHE_TTL_METRICAS_SECONDS,
    )
