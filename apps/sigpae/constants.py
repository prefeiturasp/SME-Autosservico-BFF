"""Dados estáticos da integração de métricas do SIGPAE.

Este módulo não faz nenhuma chamada de rede — só declara os parâmetros
fixos usados pelo cliente HTTP do backend de métricas do SIGPAE.
"""

CAMINHO_METRICAS = "/api/v1/sigpae/metricas/"

TIMEOUT_HTTP_SEGUNDOS = 30

CHAVE_CACHE_METRICAS = "sigpae:metricas"
