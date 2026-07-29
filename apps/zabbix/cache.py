"""Cache de estado da UI (BFF_BROKER) para as respostas do Zabbix.

A camada de request nunca chama o Zabbix diretamente — só lê o cache
aqui. Quando o cache está vazio, dispara a Celery task correspondente
em background (ver ``apps/zabbix/tasks.py``) e devolve um fallback
seguro na hora, sem bloquear a requisição.
"""

import hashlib
from typing import Any

from django.core.cache import cache


def _hash(*partes: str) -> str:
    """Gera um hash curto e estável a partir de valores arbitrários.

    Usado para compor chaves de cache a partir de query params vindos
    do frontend (project/host/system), que podem ter acentos, espaços
    ou tamanho arbitrário — evita chaves gigantes/caracteres inválidos
    no Redis e evita colisões de normalização.

    Args:
        *partes: Valores a compor no hash, na ordem recebida.

    Returns:
        Hash SHA-256 hexadecimal dos valores concatenados.
    """
    return hashlib.sha256("|".join(partes).encode()).hexdigest()


def chave_status(preset: str, host: str, project: str) -> str:
    """Chave de cache do status de disponibilidade (presets producao/filas).

    Args:
        preset: Nome do preset (``producao`` ou ``filas``).
        host: Host do Zabbix consultado.
        project: Projeto/descrição do trigger consultado.

    Returns:
        Chave de cache determinística para essa combinação.
    """
    return f"zabbix:status:{preset}:{_hash(preset, host, project)}"


def chave_jenkins(project: str, ambiente: str) -> str:
    """Chave de cache do resumo de build do Jenkins.

    Args:
        project: Nome do projeto/job consultado.
        ambiente: Ambiente consultado (``prod`` ou ``homolog``).

    Returns:
        Chave de cache determinística para essa combinação.
    """
    return f"zabbix:jenkins:{ambiente}:{_hash(ambiente, project)}"


def chave_database(sistema: str) -> str:
    """Chave de cache do status de banco de dados de um sistema.

    Args:
        sistema: Nome de exibição do sistema.

    Returns:
        Chave de cache determinística para esse sistema.
    """
    return f"zabbix:database:{_hash(sistema)}"


def obter_ou_marcar_para_atualizar(
    chave: str,
    tarefa: Any,
    args: tuple,
    *,
    ttl_lock: int,
) -> Any | None:
    """Lê o cache; se vazio, dispara a task de atualização em background.

    O lock evita disparos duplicados: se
    duas requisições chegarem quase ao mesmo tempo com o cache frio,
    só a primeira dispara a task — a segunda só encontra o lock já
    ocupado e desiste de disparar de novo (mas ainda recebe o fallback
    seguro da view).

    Args:
        chave: Chave de cache onde o valor já processado é procurado.
        tarefa: Task Celery a disparar via ``.delay(*args)`` em caso
            de cache frio (recebe a task, não o nome, para facilitar
            os testes).
        args: Argumentos posicionais repassados a ``tarefa.delay``.
        ttl_lock: Tempo de vida (segundos) do lock de atualização.

    Returns:
        O valor cacheado, ou ``None`` quando o cache estava vazio (a
        view decide o fallback seguro nesse caso).
    """
    valor = cache.get(chave)
    if valor is not None:
        return valor

    if cache.add(f"{chave}:lock", 1, timeout=ttl_lock):
        tarefa.delay(*args)
    return None
