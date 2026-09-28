"""Dados estáticos da integração de métricas do SGP.

Este módulo não faz nenhuma chamada de rede — só declara os parâmetros
fixos e a chave de cache (por ano letivo e bimestre) usados pela
orquestração das métricas do SGP.
"""

CAMINHO_METRICAS = "/api/v1/sgp/coped/metricas/"

TIMEOUT_HTTP_SEGUNDOS = 30


def chave_cache_metricas(ano_letivo: int, bimestre: int) -> str:
    """Monta a chave de cache do contrato, por ano letivo e bimestre."""
    return f"sgp:metricas:{ano_letivo}:{bimestre}"
