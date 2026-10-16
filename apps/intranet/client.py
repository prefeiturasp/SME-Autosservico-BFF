"""Cliente do backend de métricas do Intranet (chamado só pelas tasks)."""

import logging
from typing import Any

from apps.core import client_backend
from apps.intranet.constants import CAMINHO_METRICAS
from apps.intranet.constants import TIMEOUT_HTTP_SEGUNDOS

logger = logging.getLogger("bff_intranet")


def obter_metricas(periodo: str, mes: str | None) -> dict[str, Any]:
    """Busca as métricas do Intranet no backend.

    Args:
        periodo: Um de ``constants.PERIODOS``.
        mes: Mês ``AAAA-MM``; se ``None``, não é enviado.

    Returns:
        O contrato de métricas.
    """
    parametros = {"periodo": periodo}
    if mes is not None:
        parametros["mes"] = mes
    return client_backend.obter_metricas(
        CAMINHO_METRICAS,
        rotulo="Intranet",
        logger=logger,
        timeout=TIMEOUT_HTTP_SEGUNDOS,
        parametros=parametros,
    )
