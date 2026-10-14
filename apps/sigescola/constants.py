"""Dados estáticos da integração de métricas do SIG-Escola.

Este módulo não faz nenhuma chamada de rede — só declara os parâmetros
fixos e a chave de cache usados pela orquestração das métricas.
"""

from collections.abc import Mapping

from apps.core.cache import hash_chave

CAMINHO_METRICAS = "/api/v1/sigescola/metricas/"

TIMEOUT_HTTP_SEGUNDOS = 30

# Filtros aceitos, na ordem fixa usada na chave de cache.
FILTROS = ("periodo", "data_inicio", "data_fim", "dre", "ue")


def chave_cache_metricas(filtros: Mapping[str, str]) -> str:
    """Monta a chave de cache do contrato a partir dos filtros.

    Sem filtro nenhum é o cenário padrão (período corrente, rede toda), o
    único que o beat mantém quente; os demais expiram no TTL.
    """
    return "sigescola:metricas:" + hash_chave(
        *(filtros.get(nome, "") for nome in FILTROS)
    )
