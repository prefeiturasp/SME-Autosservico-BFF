"""Cliente HTTP para o backend de métricas do SERAp.

Só deve ser chamado a partir de ``apps/serap/tasks.py`` — a camada de
request síncrona (``apps/serap/api/views.py``) nunca importa este módulo,
só lê o cache. O retry de transporte vive em ``apps.core.client_backend``.
"""

import logging
from typing import Any

from apps.core import client_backend
from apps.core.client_backend import BackendMetricasError
from apps.serap.constants import CAMINHO_METRICAS
from apps.serap.constants import TIMEOUT_HTTP_SEGUNDOS

__all__ = ["BackendMetricasError", "obter_metricas"]

logger = logging.getLogger("bff_serap")


def obter_metricas(ano: int, bimestre: int) -> dict[str, Any]:
    """Busca as métricas do SERAp no backend, por ano e bimestre."""
    return client_backend.obter_metricas(
        CAMINHO_METRICAS,
        rotulo="SERAp",
        logger=logger,
        timeout=TIMEOUT_HTTP_SEGUNDOS,
        parametros={"ano": ano, "bimestre": bimestre},
    )
