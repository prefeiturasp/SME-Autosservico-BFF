"""Cliente do backend de métricas do Intranet (chamado só pelas tasks)."""

from typing import Any

from apps.core import client_backend
from apps.intranet.constants import CAMINHO_METRICAS


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
    return client_backend.obter_json(CAMINHO_METRICAS, parametros)
