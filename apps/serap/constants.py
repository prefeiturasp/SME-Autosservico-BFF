"""Dados estáticos da integração de métricas do SERAp.

Este módulo não faz nenhuma chamada de rede — só declara os parâmetros
fixos e a chave de cache (por ano e bimestre) usados pela orquestração
das métricas do SERAp.
"""

CAMINHO_METRICAS = "/api/v1/serap/provas/metricas/"

TIMEOUT_HTTP_SEGUNDOS = 30


def chave_cache_metricas(ano: int, bimestre: int) -> str:
    """Monta a chave de cache do contrato, por ano e bimestre."""
    return f"serap:metricas:{ano}:{bimestre}"
