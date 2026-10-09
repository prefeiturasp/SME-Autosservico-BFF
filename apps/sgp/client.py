"""Cliente do backend de métricas do SGP (chamado só pelas tasks)."""

from typing import Any

from apps.core import client_backend
from apps.sgp.constants import CAMINHO_METRICAS


def obter_metricas(ano_letivo: int, bimestre: int) -> dict[str, Any]:
    """Busca as métricas do SGP no backend, por ano letivo e bimestre.

    Args:
        ano_letivo: Ano letivo.
        bimestre: Bimestre.

    Returns:
        O contrato de métricas.
    """
    return client_backend.obter_json(
        CAMINHO_METRICAS, {"ano_letivo": ano_letivo, "bimestre": bimestre}
    )
