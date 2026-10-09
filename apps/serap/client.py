"""Cliente HTTP para o backend de métricas do SERAp.

Só deve ser chamado a partir de ``apps/serap/tasks.py`` — a camada de
request síncrona (``apps/serap/api/views.py``) nunca importa este módulo,
só lê o cache. O retry de transporte vive inteiramente aqui, no mesmo
formato dos clientes do SIGPAE e do SGP.
"""

import logging
import time
from typing import Any

import httpx
from django.conf import settings

from apps.serap.constants import CAMINHO_METRICAS
from apps.serap.constants import TIMEOUT_HTTP_SEGUNDOS

logger = logging.getLogger("bff_serap")

_STATUS_RETRIAVEIS = {408, 425, 429, 500, 502, 503, 504}
_MAX_TENTATIVAS = 5
_ATRASO_BASE = 1.0
_ATRASO_MAXIMO = 60.0


class BackendMetricasError(Exception):
    """Resposta inesperada do backend de métricas, não retentável."""


def _e_retriavel(exc: Exception) -> bool:
    """Indica se o erro justifica uma nova tentativa."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _STATUS_RETRIAVEIS
    return isinstance(exc, httpx.TransportError | httpx.TimeoutException)


def _aguardar_nova_tentativa(exc: Exception, tentativa: int) -> None:
    """Registra o erro e aguarda o backoff antes da próxima tentativa."""
    atraso = min(_ATRASO_BASE * (2 ** (tentativa - 1)), _ATRASO_MAXIMO)
    logger.warning(
        "SERAp: erro transitório (tentativa %d/%d) — aguardando %.1fs: %s",
        tentativa,
        _MAX_TENTATIVAS,
        atraso,
        exc,
    )
    time.sleep(atraso)


def obter_metricas(ano: int, bimestre: int) -> dict[str, Any]:
    """Busca as métricas do SERAp no backend, por ano e bimestre.

    Returns:
        O contrato de métricas já decodificado.

    Raises:
        BackendMetricasError: Resposta bem-sucedida que não é um objeto
            JSON.
        httpx.HTTPStatusError: Erro HTTP não-retentável, ou após esgotar
            as tentativas em caso de falha transitória.
    """
    url = settings.AUTOSSERVICO_BACKEND_URL.rstrip("/") + CAMINHO_METRICAS
    cabecalhos = {
        settings.API_KEY_HEADER: settings.AUTOSSERVICO_BACKEND_API_KEY
    }
    parametros = {"ano": ano, "bimestre": bimestre}

    tentativa = 0
    while True:
        try:
            with httpx.Client(timeout=TIMEOUT_HTTP_SEGUNDOS) as cliente:
                resposta = cliente.get(
                    url, headers=cabecalhos, params=parametros
                )
            resposta.raise_for_status()
            dados = resposta.json()
            if not isinstance(dados, dict):
                raise BackendMetricasError(
                    "Resposta não-JSON do backend de métricas"
                )
            return dados
        except (
            httpx.TransportError,
            httpx.HTTPStatusError,
            httpx.TimeoutException,
        ) as exc:
            tentativa += 1
            if not _e_retriavel(exc) or tentativa >= _MAX_TENTATIVAS:
                logger.exception(
                    "SERAp: GET %s falhou após %d tentativa(s)",
                    url,
                    tentativa,
                )
                raise
            _aguardar_nova_tentativa(exc, tentativa)
