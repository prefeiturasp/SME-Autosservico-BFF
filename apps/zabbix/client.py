"""Cliente JSON-RPC para o Zabbix.

Só deve ser chamado a partir de ``apps/zabbix/tasks.py`` — a camada de
request síncrona (``apps/zabbix/api/views.py``) nunca importa este
módulo diretamente, só lê o cache (ver ``apps/zabbix/cache.py``).
"""

import logging
import time
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger("bff_zabbix")

_STATUS_RETRIAVEIS = {408, 425, 429, 500, 502, 503, 504}
_MAX_TENTATIVAS = 5
_ATRASO_BASE = 1.0
_ATRASO_MAXIMO = 60.0


class ZabbixRpcError(Exception):
    """Erro de negócio retornado pelo Zabbix.

    Levantado quando a resposta HTTP é bem-sucedida, mas o corpo não é
    JSON válido ou traz uma chave ``error`` no envelope JSON-RPC — em
    nenhum dos dois casos a chamada deve ser repetida.
    """


def _cabecalhos() -> dict[str, str]:
    """Monta os cabeçalhos de autenticação para o Zabbix.

    O Zabbix autentica via chave de API estática enviada como Bearer
    token.

    Returns:
        Cabeçalhos com Content-Type e Authorization.
    """
    return {
        "Content-Type": "application/json-rpc",
        "Authorization": f"Bearer {settings.ZABBIX_API_TOKEN}",
    }


def _e_retriavel(exc: Exception) -> bool:
    """Indica se o erro justifica uma nova tentativa.

    Erros de transporte/timeout são sempre retentáveis. Erros HTTP só
    são retentáveis quando o status indica falha transitória do
    servidor (ex.: 503) — status como 400/404 são erro de payload ou
    de rota e nunca vão se resolver sozinhos com retry.

    Args:
        exc: Exceção capturada na chamada ao Zabbix.

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
        "Zabbix: erro transitório (tentativa %d/%d) — aguardando %.1fs: %s",
        tentativa,
        _MAX_TENTATIVAS,
        atraso,
        exc,
    )
    time.sleep(atraso)


def _extrair_resultado(dados: Any) -> Any:
    """Valida o envelope JSON-RPC e extrai o campo ``result``.

    Args:
        dados: Corpo já decodificado da resposta HTTP.

    Returns:
        O valor de ``dados["result"]``.

    Raises:
        ZabbixRpcError: Quando a resposta não é um objeto JSON,
            ou quando o envelope JSON-RPC traz uma chave ``error``.
    """
    if isinstance(dados, str) or not isinstance(dados, dict):
        raise ZabbixRpcError("Resposta não-JSON do Zabbix")
    erro = dados.get("error")
    if erro:
        mensagem = f"Zabbix {erro.get('code')}: {erro.get('message')}"
        if erro.get("data"):
            mensagem += f" - {erro['data']}"
        raise ZabbixRpcError(mensagem)
    return dados.get("result")


def zabbix_rpc(
    method: str,
    params: dict,
    *,
    id_requisicao: int = 1,
    max_tentativas: int | None = None,
) -> Any:
    """Executa uma chamada JSON-RPC 2.0 contra a API do Zabbix.

    Args:
        method: Nome do método Zabbix.
        params: Parâmetros do método.
        id_requisicao: Id da requisição JSON-RPC.
        max_tentativas: Número máximo de tentativas para falhas
            transitórias de transporte/HTTP. Usa o padrão do módulo
            (5) quando omitido.

    Returns:
        O campo ``result`` da resposta JSON-RPC.

    Raises:
        ZabbixRpcError: Erro de negócio do Zabbix nunca repetido.
        httpx.HTTPStatusError: Erro HTTP não-retentável, ou após
            esgotar as tentativas em caso de falha transitória.
        httpx.TransportError: Após esgotar as tentativas por falha de
            conexão.
        httpx.TimeoutException: Após esgotar as tentativas por timeout.
    """
    limite = max_tentativas or _MAX_TENTATIVAS
    corpo = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": id_requisicao,
    }

    tentativa = 0
    while True:
        try:
            with httpx.Client(timeout=settings.ZABBIX_HTTP_TIMEOUT) as cliente:
                resposta = cliente.post(
                    settings.ZABBIX_API_URL, json=corpo, headers=_cabecalhos()
                )
            resposta.raise_for_status()
            try:
                dados = resposta.json()
            except ValueError as exc:
                raise ZabbixRpcError("Resposta não-JSON do Zabbix") from exc
            return _extrair_resultado(dados)
        except (
            httpx.TransportError,
            httpx.HTTPStatusError,
            httpx.TimeoutException,
        ) as exc:
            tentativa += 1
            if not _e_retriavel(exc) or tentativa >= limite:
                logger.exception(
                    "Zabbix: %s falhou após %d tentativa(s)",
                    method,
                    tentativa,
                )
                raise
            _aguardar_nova_tentativa(exc, tentativa)
