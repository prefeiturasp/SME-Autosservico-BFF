"""Celery tasks da integração de métricas do SIG-Escola.

O retry de transporte já é feito dentro de ``apps.sigescola.client``; a
task consulta o backend e grava o resultado na chave da combinação de
filtros. Como no SERAp, contrato degradado (``atualizado_em`` nulo, por
falha de banco) não é gravado: a próxima requisição tenta de novo, em vez
de servir blocos nulos até o TTL vencer.
"""

import logging
from collections.abc import Mapping

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from apps.sigescola import client
from apps.sigescola.constants import chave_cache_metricas

logger = logging.getLogger("bff_sigescola")


@shared_task(name="sigescola.atualizar_metricas")
def atualizar_metricas(filtros: Mapping[str, str]) -> None:
    """Consulta o backend e atualiza o cache das métricas do SIG-Escola."""
    resultado = client.obter_metricas(filtros)
    if resultado.get("atualizado_em") is None:
        logger.warning(
            "SIG-Escola: backend devolveu métricas degradadas (atualizado_em "
            "nulo) para filtros=%s — cache não atualizado",
            dict(filtros),
        )
        return
    cache.set(
        chave_cache_metricas(filtros),
        resultado,
        timeout=settings.SIGESCOLA_CACHE_TTL_METRICAS_SECONDS,
    )


@shared_task(name="sigescola.aquecer_padrao")
def aquecer_padrao() -> None:
    """Mantém quente o cenário padrão da tela (via beat).

    Sem filtros = período corrente do PTRF e rede toda; quem resolve o
    período é o backend.
    """
    atualizar_metricas({})
