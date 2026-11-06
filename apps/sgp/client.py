"""Cliente HTTP para o backend de métricas do SGP.

Só deve ser chamado a partir de ``apps/sgp/tasks.py``: a camada de
request síncrona (``apps/sgp/api/views.py``) nunca importa este módulo,
só lê o cache. O retry de transporte vive em ``apps.core.client_backend``.
"""

import logging
from typing import Any

from apps.core import client_backend
from apps.core.client_backend import BackendMetricasError
from apps.sgp.constants import CAMINHO_METRICAS
from apps.sgp.constants import CAMINHO_PERIODOS
from apps.sgp.constants import TIMEOUT_HTTP_SEGUNDOS

__all__ = ["BackendMetricasError", "obter_metricas", "obter_periodos"]

logger = logging.getLogger("bff_sgp")


def obter_metricas(
    ano_letivo: int, segmento: str, semestre: int | None, bimestre: int
) -> dict[str, Any]:
    """Busca as métricas do SGP no backend."""
    parametros: dict[str, Any] = {
        "ano_letivo": ano_letivo,
        "bimestre": bimestre,
        "segmento": segmento,
    }
    if semestre is not None:
        parametros["semestre"] = semestre
    return client_backend.obter_metricas(
        CAMINHO_METRICAS,
        rotulo="SGP",
        logger=logger,
        timeout=TIMEOUT_HTTP_SEGUNDOS,
        parametros=parametros,
    )


def obter_periodos() -> dict[str, Any]:
    """Busca no backend as opções do filtro de período do SGP."""
    return client_backend.obter_metricas(
        CAMINHO_PERIODOS,
        rotulo="SGP",
        logger=logger,
        timeout=TIMEOUT_HTTP_SEGUNDOS,
    )
