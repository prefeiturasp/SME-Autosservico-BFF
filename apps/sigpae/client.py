"""Cliente do backend de métricas do SIGPAE (chamado só pelas tasks)."""

from typing import Any

from apps.core import client_backend
from apps.sigpae.constants import CAMINHO_METRICAS


def obter_metricas() -> dict[str, Any]:
    """Busca as métricas do SIGPAE no backend.

    Returns:
        O contrato de métricas.
    """
    return client_backend.obter_json(CAMINHO_METRICAS)
