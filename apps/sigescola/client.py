"""Cliente HTTP para o backend de métricas do SIG-Escola.

Só deve ser chamado a partir de ``apps/sigescola/tasks.py`` — a camada de
request síncrona (``apps/sigescola/api/views.py``) nunca importa este
módulo, só lê o cache. O retry de transporte vive em
``apps.core.client_backend``.
"""

import logging
from collections.abc import Mapping
from typing import Any

from apps.core import client_backend
from apps.core.client_backend import BackendMetricasError
from apps.sigescola.constants import CAMINHO_METRICAS
from apps.sigescola.constants import TIMEOUT_HTTP_SEGUNDOS

__all__ = ["BackendMetricasError", "obter_metricas"]

logger = logging.getLogger("bff_sigescola")


def obter_metricas(filtros: Mapping[str, str]) -> dict[str, Any]:
    """Busca as métricas do SIG-Escola no backend, com os filtros da tela."""
    return client_backend.obter_metricas(
        CAMINHO_METRICAS,
        rotulo="SIG-Escola",
        logger=logger,
        timeout=TIMEOUT_HTTP_SEGUNDOS,
        parametros=dict(filtros),
    )
