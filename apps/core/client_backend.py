"""Cliente HTTP do SME-Autosservico-Backend, compartilhado pelos domínios.

Chamado só pelas tasks (via ``apps/<dominio>/client.py``). O retry com
backoff fica todo aqui.
"""

import logging
import time
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger("bff_backend")

TIMEOUT_HTTP_SEGUNDOS = 30

_STATUS_RETRIAVEIS = {408, 425, 429, 500, 502, 503, 504}
_MAX_TENTATIVAS = 5
_ATRASO_BASE = 1.0
_ATRASO_MAXIMO = 60.0


class BackendMetricasError(Exception):
    """Resposta inesperada do backend de métricas, não retentável."""


def _deve_repetir(exc: Exception, tentativa: int) -> bool:
    """Indica se ainda vale tentar de novo após ``exc``."""
    if tentativa >= _MAX_TENTATIVAS:
        return False
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _STATUS_RETRIAVEIS
    return True


def _aguardar(exc: Exception, url: str, tentativa: int) -> None:
    """Loga o erro e espera o backoff exponencial da ``tentativa``."""
    atraso = min(_ATRASO_BASE * 2 ** (tentativa - 1), _ATRASO_MAXIMO)
    logger.warning(
        "GET %s: erro transitório (tentativa %d/%d) — aguardando %.1fs: %s",
        url,
        tentativa,
        _MAX_TENTATIVAS,
        atraso,
        exc,
    )
    time.sleep(atraso)


def obter_json(
    caminho: str, parametros: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Faz um GET no backend e devolve o corpo JSON.

    Args:
        caminho: Caminho da rota no backend (ex.: ``/api/v1/sgp/...``).
        parametros: Query string, se houver.

    Returns:
        O corpo da resposta decodificado.

    Raises:
        BackendMetricasError: Resposta que não é um objeto JSON.
        httpx.HTTPStatusError: Erro não retentável ou tentativas
            esgotadas.
    """
    url = settings.AUTOSSERVICO_BACKEND_URL.rstrip("/") + caminho
    cabecalhos = {
        settings.API_KEY_HEADER: settings.AUTOSSERVICO_BACKEND_API_KEY
    }

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
            if not _deve_repetir(exc, tentativa):
                logger.exception(
                    "GET %s falhou após %d tentativa(s)", url, tentativa
                )
                raise
            _aguardar(exc, url, tentativa)
