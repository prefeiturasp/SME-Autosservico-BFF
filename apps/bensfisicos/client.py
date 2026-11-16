"""Cliente HTTP para o backend de métricas do Bens Físicos.

Só deve ser chamado a partir de ``apps/bensfisicos/tasks.py``; a view só
lê o cache. O retry de transporte vive em ``apps.core.client_backend``.
"""

import logging
from typing import Any

from apps.bensfisicos.constants import CAMINHO_METRICAS
from apps.bensfisicos.constants import TIMEOUT_HTTP_SEGUNDOS
from apps.core import client_backend
from apps.core.client_backend import BackendMetricasError

__all__ = ["BackendMetricasError", "obter_metricas"]

logger = logging.getLogger("bff_bensfisicos")


def obter_metricas() -> dict[str, Any]:
    """Busca as métricas do Bens Físicos no backend do autosserviço."""
    return client_backend.obter_metricas(
        CAMINHO_METRICAS,
        rotulo="Bens Físicos",
        logger=logger,
        timeout=TIMEOUT_HTTP_SEGUNDOS,
    )
