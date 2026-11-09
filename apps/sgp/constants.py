"""Dados estáticos da integração de métricas do SGP.

Este módulo não faz nenhuma chamada de rede: só declara os parâmetros
fixos e as chaves de cache usadas pela orquestração das métricas do SGP.
"""

CAMINHO_METRICAS = "/api/v1/sgp/coped/metricas/"
CAMINHO_PERIODOS = "/api/v1/sgp/coped/periodos/"

TIMEOUT_HTTP_SEGUNDOS = 30

SEGMENTO_FUNDAMENTAL_MEDIO = "fundamental_medio"
SEGMENTO_EJA = "eja"
SEGMENTOS = (SEGMENTO_FUNDAMENTAL_MEDIO, SEGMENTO_EJA)
BIMESTRES_POR_SEGMENTO = {SEGMENTO_FUNDAMENTAL_MEDIO: 4, SEGMENTO_EJA: 2}

CHAVE_CACHE_PERIODOS = "sgp:periodos"


def chave_cache_metricas(
    ano_letivo: int, segmento: str, semestre: int | None, bimestre: int
) -> str:
    """Monta a chave de cache do contrato, por período e segmento."""
    return f"sgp:metricas:{ano_letivo}:{segmento}:{semestre or 0}:{bimestre}"
