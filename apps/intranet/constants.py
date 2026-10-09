"""Constantes da integração de métricas do Intranet."""

CAMINHO_METRICAS = "/api/v1/intranet/metricas/"

TIMEOUT_HTTP_SEGUNDOS = 30

PERIODO_GERAL = "geral"

# Mesmos valores aceitos pelo backend.
PERIODOS = (PERIODO_GERAL, "dia", "quinzena", "mes", "trimestre")


def chave_cache_metricas(periodo: str, mes: str | None) -> str:
    """Monta a chave de cache do contrato, por período e mês."""
    return f"intranet:metricas:{periodo}:{mes or PERIODO_GERAL}"
