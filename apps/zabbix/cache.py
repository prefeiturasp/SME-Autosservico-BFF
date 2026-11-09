"""Cache de estado da UI (BFF_BROKER) para as respostas do Zabbix.

A camada de request nunca chama o Zabbix diretamente — só lê o cache
aqui. Quando o cache está vazio, dispara a Celery task correspondente
em background (ver ``apps/zabbix/tasks.py``) e devolve um fallback
seguro na hora, sem bloquear a requisição.
"""

from apps.core.cache import hash_chave as _hash
from apps.core.cache import obter_ou_marcar_para_atualizar

__all__ = [
    "chave_controle_acessos",
    "chave_database",
    "chave_jenkins",
    "chave_serie_acessos",
    "chave_status",
    "obter_ou_marcar_para_atualizar",
]


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


def chave_controle_acessos() -> str:
    """Chave de cache do controle de acessos do SGP."""
    return "zabbix:sgp:controle_acessos"


def chave_serie_acessos(granularidade: str) -> str:
    """Chave de cache da série do gráfico de acessos do SGP.

    Args:
        granularidade: ``hora``, ``dia``, ``mes`` ou ``ano``.

    Returns:
        Chave de cache por granularidade.
    """
    return f"zabbix:sgp:controle_acessos:serie:{granularidade}"
