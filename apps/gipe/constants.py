"""Dados estáticos da integração de métricas do GIPE.

Este módulo não faz nenhuma chamada de rede — só declara os parâmetros
fixos, a chave de cache (por ano letivo) e o ano letivo corrente usados
pela orquestração das métricas.
"""

from django.utils import timezone

CAMINHO_METRICAS = "/api/v1/gipe/metricas/"

# O backend leva ~10 s por ano letivo com o cache dele frio.
TIMEOUT_HTTP_SEGUNDOS = 30


def chave_cache_metricas(ano_letivo: int) -> str:
    """Monta a chave de cache do contrato, por ano letivo."""
    return f"gipe:metricas:{ano_letivo}"


def ano_letivo_corrente() -> int:
    """Ano letivo corrente: o ano civil da data local.

    É uma função (e não uma constante) para virar o ano sem reiniciar o
    worker nem o beat.
    """
    return timezone.localdate().year
