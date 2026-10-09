"""Cliente HTTP para o backend de métricas do SGP.

Só deve ser chamado a partir de ``apps/sgp/tasks.py`` — a camada de
request síncrona (``apps/sgp/api/views.py``) nunca importa este módulo,
só lê o cache. O retry de transporte vive em ``apps.core.client_backend``.
"""

import logging
from typing import Any

from apps.core import client_backend
from apps.core.client_backend import BackendMetricasError
from apps.sgp.constants import CAMINHO_METRICAS
from apps.sgp.constants import TIMEOUT_HTTP_SEGUNDOS

__all__ = ["BackendMetricasError", "obter_metricas"]

logger = logging.getLogger("bff_sgp")


def obter_metricas(ano_letivo: int, bimestre: int) -> dict[str, Any]:
    """Busca as métricas do SGP no backend, por ano letivo e bimestre."""
    return client_backend.obter_metricas(
        CAMINHO_METRICAS,
        rotulo="SGP",
        logger=logger,
        timeout=TIMEOUT_HTTP_SEGUNDOS,
        parametros={"ano_letivo": ano_letivo, "bimestre": bimestre},
    )
