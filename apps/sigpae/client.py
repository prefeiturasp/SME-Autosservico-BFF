"""Cliente HTTP para o backend de métricas do SIGPAE.

Só deve ser chamado a partir de ``apps/sigpae/tasks.py`` — a camada de
request síncrona (``apps/sigpae/api/views.py``) nunca importa este módulo,
só lê o cache. O retry de transporte vive em ``apps.core.client_backend``.
"""

import logging
from typing import Any

from apps.core import client_backend
from apps.core.client_backend import BackendMetricasError
from apps.sigpae.constants import CAMINHO_METRICAS
from apps.sigpae.constants import TIMEOUT_HTTP_SEGUNDOS

__all__ = ["BackendMetricasError", "obter_metricas"]

logger = logging.getLogger("bff_sigpae")


def obter_metricas() -> dict[str, Any]:
    """Busca as métricas do SIGPAE no backend do autosserviço."""
    return client_backend.obter_metricas(
        CAMINHO_METRICAS,
        rotulo="SIGPAE",
        logger=logger,
        timeout=TIMEOUT_HTTP_SEGUNDOS,
    )
