"""Cliente HTTP do backend do autosserviço (métricas por sistema).

GET autenticado pelo header ``API_KEY_HEADER``, com retry/backoff de
transporte. Usado pelos clientes do SIGPAE, do SGP e do SERAp, que só
informam o caminho, os parâmetros e o rótulo dos logs. Só deve ser chamado
a partir das tasks Celery — as views só leem o cache.
"""

import logging
import time
from typing import Any

import httpx
from django.conf import settings

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


def obter_metricas(
    caminho: str,
    *,
    rotulo: str,
    logger: logging.Logger,
    timeout: float,
    parametros: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Busca um contrato de métricas no backend do autosserviço.

    Args:
        caminho: Caminho do endpoint no backend (ex.: ``/api/v1/...``).
        rotulo: Nome do sistema usado nos logs (ex.: ``"SGP"``).
        logger: Logger do app chamador.
        timeout: Timeout HTTP, em segundos.
        parametros: Query string, quando o endpoint é parametrizado.

    Returns:
        O contrato de métricas já decodificado.

    Raises:
        BackendMetricasError: Resposta bem-sucedida que não é um objeto
            JSON.
        httpx.HTTPStatusError: Erro HTTP não-retentável, ou após esgotar
            as tentativas em caso de falha transitória.
    """
    url = settings.AUTOSSERVICO_BACKEND_URL.rstrip("/") + caminho
    cabecalhos = {
        settings.API_KEY_HEADER: settings.AUTOSSERVICO_BACKEND_API_KEY
    }

    tentativa = 0
    while True:
        try:
            with httpx.Client(timeout=timeout) as cliente:
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
                    "%s: GET %s falhou após %d tentativa(s)",
                    rotulo,
                    url,
                    tentativa,
                )
                raise
            atraso = min(_ATRASO_BASE * (2 ** (tentativa - 1)), _ATRASO_MAXIMO)
            logger.warning(
                "%s: erro transitório (tentativa %d/%d) — "
                "aguardando %.1fs: %s",
                rotulo,
                tentativa,
                _MAX_TENTATIVAS,
                atraso,
                exc,
            )
            time.sleep(atraso)
