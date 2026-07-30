"""Cliente HTTP para a REST API do Azure DevOps.

Só deve ser chamado a partir de ``apps/azure/tasks.py`` — a camada de
request síncrona (``apps/azure/api/views.py``) nunca importa este módulo
diretamente, só lê o cache (ver ``apps/azure/cache.py``).

O retry de transporte vive inteiramente aqui, no mesmo formato do
cliente do Zabbix (``apps/zabbix/client.py``): as tasks não usam retry
próprio.
"""

import base64
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx
from django.conf import settings

from apps.azure.constants import TIMEOUT_HTTP_SEGUNDOS
from apps.azure.constants import URL_BASE_API

logger = logging.getLogger("bff_azure")

_STATUS_RETRIAVEIS = {408, 425, 429, 500, 502, 503, 504}
_MAX_TENTATIVAS = 5
_ATRASO_BASE = 1.0
_ATRASO_MAXIMO = 60.0


class AzureApiError(Exception):
    """Erro de negócio retornado pelo Azure DevOps.

    Levantado quando a resposta HTTP é bem-sucedida, mas o corpo não é um
    objeto JSON válido — o caso típico é o Azure devolver a página HTML
    de login quando o PAT está inválido ou expirado, respondendo 200. Em
    nenhuma dessas situações a chamada deve ser repetida.
    """


def _cabecalhos() -> dict[str, str]:
    """Monta os cabeçalhos de autenticação para o Azure DevOps.

    O Azure DevOps autentica o Personal Access Token via HTTP Basic, com
    o usuário vazio e o PAT como senha.

    Returns:
        Cabeçalhos com Content-Type e Authorization.
    """
    pat = settings.AZURE_DEVOPS_PAT or ""
    credencial = base64.b64encode(f":{pat}".encode()).decode()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {credencial}",
    }


def montar_url(organizacao: str, projeto: str, recurso: str) -> str:
    """Monta a URL de um recurso da REST API do Azure DevOps.

    A organização e o projeto são percent-encoded porque vêm de
    parâmetros externos e costumam ter espaços e acentos (ex.:
    ``"SME - Sustentação"``). O recurso é sempre uma constante do
    próprio código, então preserva as barras.

    Args:
        organizacao: Nome da organização no Azure DevOps.
        projeto: Nome do projeto (vazio para recursos de organização).
        recurso: Caminho do recurso (ex.: ``"_apis/wit/wiql"``).

    Returns:
        URL absoluta pronta para a requisição.
    """
    base = URL_BASE_API.rstrip("/")
    partes = [quote(organizacao, safe="")]
    if projeto:
        partes.append(quote(projeto, safe=""))
    partes.append(recurso.lstrip("/"))
    return f"{base}/{'/'.join(partes)}"


def _e_retriavel(exc: Exception) -> bool:
    """Indica se o erro justifica uma nova tentativa.

    Erros de transporte/timeout são sempre retentáveis. Erros HTTP só são
    retentáveis quando o status indica falha transitória do servidor
    (ex.: 503) — status como 401/404 são erro de credencial ou de rota e
    nunca vão se resolver sozinhos com retry.

    Args:
        exc: Exceção capturada na chamada ao Azure DevOps.

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
        "Azure: erro transitório (tentativa %d/%d) — aguardando %.1fs: %s",
        tentativa,
        _MAX_TENTATIVAS,
        atraso,
        exc,
    )
    time.sleep(atraso)


def _extrair_corpo(dados: Any) -> dict[str, Any]:
    """Valida que o corpo da resposta é um objeto JSON.

    Args:
        dados: Corpo já decodificado da resposta HTTP.

    Returns:
        O corpo como dicionário.

    Raises:
        AzureApiError: Quando a resposta não é um objeto JSON.
    """
    if isinstance(dados, str) or not isinstance(dados, dict):
        raise AzureApiError("Resposta não-JSON do Azure DevOps")
    corpo: dict[str, Any] = dados
    return corpo


def azure_request(
    metodo: str,
    url: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
    max_tentativas: int | None = None,
) -> dict[str, Any]:
    """Executa uma chamada e devolve só o corpo da resposta.

    Atalho para ``azure_request_com_cabecalhos`` nos recursos que não
    precisam ler nenhum header (a maioria).

    Args:
        metodo: Método HTTP (``"GET"`` ou ``"POST"``).
        url: URL absoluta do recurso, montada por ``montar_url``.
        params: Query params da requisição (inclui ``api-version``).
        json_body: Corpo JSON da requisição, quando aplicável.
        max_tentativas: Número máximo de tentativas para falhas
            transitórias.

    Returns:
        O corpo da resposta já decodificado.
    """
    corpo, _cabecalhos_resposta = azure_request_com_cabecalhos(
        metodo,
        url,
        params=params,
        json_body=json_body,
        max_tentativas=max_tentativas,
    )
    return corpo


def azure_request_com_cabecalhos(
    metodo: str,
    url: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
    max_tentativas: int | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Executa uma chamada HTTP contra a REST API do Azure DevOps.

    Args:
        metodo: Método HTTP (``"GET"`` ou ``"POST"``).
        url: URL absoluta do recurso, montada por ``montar_url``.
        params: Query params da requisição (inclui ``api-version``).
        json_body: Corpo JSON da requisição, quando aplicável.
        max_tentativas: Número máximo de tentativas para falhas
            transitórias de transporte/HTTP. Usa o padrão do módulo (5)
            quando omitido.

    Returns:
        Tupla ``(corpo, cabeçalhos)`` — os cabeçalhos importam na
        paginação de projetos, que devolve o token de continuação em
        ``x-ms-continuationtoken``.

    Raises:
        AzureApiError: Resposta bem-sucedida que não é um objeto JSON,
            nunca repetida.
        httpx.HTTPStatusError: Erro HTTP não-retentável, ou após esgotar
            as tentativas em caso de falha transitória.
        httpx.TransportError: Após esgotar as tentativas por falha de
            conexão.
        httpx.TimeoutException: Após esgotar as tentativas por timeout.
    """
    limite = max_tentativas or _MAX_TENTATIVAS

    tentativa = 0
    while True:
        try:
            with httpx.Client(timeout=TIMEOUT_HTTP_SEGUNDOS) as cliente:
                resposta = cliente.request(
                    metodo,
                    url,
                    params=params,
                    json=json_body,
                    headers=_cabecalhos(),
                )
            resposta.raise_for_status()
            try:
                dados = resposta.json()
            except ValueError as exc:
                raise AzureApiError(
                    "Resposta não-JSON do Azure DevOps"
                ) from exc
            return _extrair_corpo(dados), dict(resposta.headers)
        except (
            httpx.TransportError,
            httpx.HTTPStatusError,
            httpx.TimeoutException,
        ) as exc:
            tentativa += 1
            if not _e_retriavel(exc) or tentativa >= limite:
                logger.exception(
                    "Azure: %s %s falhou após %d tentativa(s)",
                    metodo,
                    url,
                    tentativa,
                )
                raise
            _aguardar_nova_tentativa(exc, tentativa)
