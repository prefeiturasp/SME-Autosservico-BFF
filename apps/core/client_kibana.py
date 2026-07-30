"""Cliente do proxy de busca do Kibana (``/internal/search/es``).

Infraestrutura genérica reaproveitável por qualquer domínio de métricas
que precise ler dados já indexados no Elasticsearch da SME via Kibana
(ver POC ``poc-sgp-elasticsearch``). Só deve ser chamado a partir de uma
Celery task — a camada de request síncrona nunca importa este módulo
diretamente, mesma regra do ``apps/zabbix/client.py``.
"""

import logging
import time
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger("bff_core")

_STATUS_RETRIAVEIS = {408, 425, 429, 500, 502, 503, 504}
_MAX_TENTATIVAS = 5
_ATRASO_BASE = 1.0
_ATRASO_MAXIMO = 60.0


class KibanaSearchError(Exception):
    """Erro de negócio retornado pelo proxy de busca do Kibana.

    Levantado quando a resposta HTTP é bem-sucedida, mas o corpo não é
    JSON válido — nesse caso a chamada não deve ser repetida.
    """


def _e_retriavel(exc: Exception) -> bool:
    """Indica se o erro justifica uma nova tentativa.

    Args:
        exc: Exceção capturada na chamada ao Kibana.

    Returns:
        ``True`` se a chamada deve ser repetida.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _STATUS_RETRIAVEIS
    return isinstance(exc, httpx.TransportError | httpx.TimeoutException)


def _aguardar_nova_tentativa(exc: Exception, tentativa: int) -> None:
    """Registra o erro e aguarda o backoff antes da próxima tentativa.

    Args:
        exc: Exceção que motivou a nova tentativa.
        tentativa: Número da tentativa que acabou de falhar.
    """
    atraso = min(_ATRASO_BASE * (2 ** (tentativa - 1)), _ATRASO_MAXIMO)
    logger.warning(
        "Kibana: erro transitório (tentativa %d/%d) — aguardando %.1fs: %s",
        tentativa,
        _MAX_TENTATIVAS,
        atraso,
        exc,
    )
    time.sleep(atraso)


def kibana_search(
    index: str,
    body: dict[str, Any],
    *,
    max_tentativas: int | None = None,
) -> dict[str, Any]:
    """Executa uma busca Elasticsearch através do proxy do Kibana.

    Args:
        index: Nome do índice a consultar (ex.: ``prod_metricas_sgp_acessos``).
        body: Corpo da query Elasticsearch (DSL), incluindo agregações.
        max_tentativas: Número máximo de tentativas para falhas
            transitórias de transporte/HTTP. Usa o padrão do módulo
            (5) quando omitido.

    Returns:
        O corpo já decodificado da resposta do Kibana.

    Raises:
        KibanaSearchError: Resposta bem-sucedida, mas não-JSON.
        httpx.HTTPStatusError: Erro HTTP não-retentável, ou após
            esgotar as tentativas em caso de falha transitória.
        httpx.TransportError: Após esgotar as tentativas por falha de
            conexão.
        httpx.TimeoutException: Após esgotar as tentativas por timeout.
    """
    limite = max_tentativas or _MAX_TENTATIVAS
    url = f"{settings.KIBANA_URL.rstrip('/')}/internal/search/es"
    corpo = {"params": {"index": index, "body": body}}
    auth = (settings.KIBANA_USERNAME, settings.KIBANA_PASSWORD)

    tentativa = 0
    while True:
        try:
            with httpx.Client(timeout=settings.KIBANA_HTTP_TIMEOUT) as cliente:
                resposta = cliente.post(url, json=corpo, auth=auth)
            resposta.raise_for_status()
            try:
                dados: dict[str, Any] = resposta.json()
            except ValueError as exc:
                raise KibanaSearchError("Resposta não-JSON do Kibana") from exc
            return dados
        except (
            httpx.TransportError,
            httpx.HTTPStatusError,
            httpx.TimeoutException,
        ) as exc:
            tentativa += 1
            if not _e_retriavel(exc) or tentativa >= limite:
                logger.exception(
                    "Kibana: busca em %s falhou após %d tentativa(s)",
                    index,
                    tentativa,
                )
                raise
            _aguardar_nova_tentativa(exc, tentativa)
