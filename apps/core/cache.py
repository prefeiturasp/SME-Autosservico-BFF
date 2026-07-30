"""Utilidades de cache compartilhadas entre os apps de domínio.

Concentra o padrão cache-aside descrito na arquitetura C3: a camada de
request nunca faz I/O externo, apenas lê o estado já processado no
``BFF_BROKER`` (KeyDB) e, em cache frio, delega a atualização para uma
Celery task em background.
"""

import hashlib
from typing import Any

from django.core.cache import cache


def hash_chave(*partes: str) -> str:
    """Gera um hash curto e estável a partir de valores arbitrários.

    Usado para compor chaves de cache a partir de parâmetros vindos do
    frontend (project/host/system/filtros), que podem ter acentos,
    espaços ou tamanho arbitrário — evita chaves gigantes/caracteres
    inválidos no Redis e evita colisões de normalização.

    Args:
        *partes: Valores a compor no hash, na ordem recebida.

    Returns:
        Hash SHA-256 hexadecimal dos valores concatenados.
    """
    return hashlib.sha256("|".join(partes).encode()).hexdigest()


def obter_ou_marcar_para_atualizar(
    chave: str,
    tarefa: Any,
    args: tuple,
    *,
    ttl_lock: int,
) -> Any | None:
    """Lê o cache; se vazio, dispara a task de atualização em background.

    O lock evita disparos duplicados: se duas requisições chegarem quase
    ao mesmo tempo com o cache frio, só a primeira dispara a task — a
    segunda só encontra o lock já ocupado e desiste de disparar de novo
    (mas ainda recebe o fallback seguro da view).

    Args:
        chave: Chave de cache onde o valor já processado é procurado.
        tarefa: Task Celery a disparar via ``.delay(*args)`` em caso de
            cache frio (recebe a task, não o nome, para facilitar os
            testes).
        args: Argumentos posicionais repassados a ``tarefa.delay``.
        ttl_lock: Tempo de vida (segundos) do lock de atualização.

    Returns:
        O valor cacheado, ou ``None`` quando o cache estava vazio (a view
        decide o fallback seguro nesse caso).
    """
    valor = cache.get(chave)
    if valor is not None:
        return valor

    if cache.add(f"{chave}:lock", 1, timeout=ttl_lock):
        tarefa.delay(*args)
    return None
