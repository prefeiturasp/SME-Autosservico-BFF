"""Dados estáticos usados nas integrações com o Zabbix.

Este módulo não faz nenhuma chamada de rede — só declara os parâmetros
fixos usados pelos serviços (``apps/zabbix/services/``) para montar as
requisições ao Zabbix.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


def avaliar_mysql_ping(lastvalue: str) -> bool:
    """Indica se um MySQL está disponível a partir do item ``mysql.ping``.

    Args:
        lastvalue: Último valor do item no Zabbix.

    Returns:
        ``True`` quando o ping do MySQL respondeu (``lastvalue == "1"``).
    """
    return lastvalue == "1"


def avaliar_psql_running(lastvalue: str) -> bool:
    """Indica se um PostgreSQL está disponível via o item ``psql.running``.

    Atenção: a semântica deste item é invertida em relação ao
    ``mysql.ping`` — o serviço "rodando" é reportado como ``"0"``, não
    ``"1"``. Isso é assim na configuração do Zabbix, não um erro de
    porte.

    Args:
        lastvalue: Último valor do item no Zabbix.

    Returns:
        ``True`` quando o serviço está rodando (``lastvalue == "0"``).
    """
    return lastvalue == "0"


def avaliar_sqlserver_running(lastvalue: str) -> bool:
    """Indica se um SQL Server está disponível a partir do item de serviço.

    Mesma semântica invertida do ``psql_running`` (``"0"`` = rodando).

    Args:
        lastvalue: Último valor do item no Zabbix.

    Returns:
        ``True`` quando o serviço está rodando (``lastvalue == "0"``).
    """
    return lastvalue == "0"


@dataclass(frozen=True)
class ConfiguracaoInstanciaBanco:
    """Configuração de uma instância de banco monitorada via Zabbix."""

    label: str
    hostid: str
    key: str
    db_type: Literal["mysql", "postgresql", "sqlserver"]
    avaliar_disponibilidade: Callable[[str], bool]
    role: Literal["escrita", "leitura"] | None = None


_ITEM_KEY_PSQL_RUNNING = "psql.running"

_MYSQL_PORTAL = ConfiguracaoInstanciaBanco(
    label="MySQL",
    hostid="10641",
    key="mysql.ping",
    db_type="mysql",
    avaliar_disponibilidade=avaliar_mysql_ping,
)
_POSTGRES_PADRAO = ConfiguracaoInstanciaBanco(
    label="PostgreSQL",
    hostid="10605",
    key=_ITEM_KEY_PSQL_RUNNING,
    db_type="postgresql",
    avaliar_disponibilidade=avaliar_psql_running,
)

# Mapeia o nome de exibição do sistema (mesmo valor enviado pelo
# frontend no query param `system`) para as instâncias de banco
# monitoradas no Zabbix. Sistemas ausentes daqui, ou com lista vazia
# (ex.: "Escolhas"), são tratados como "sem banco de dados" — resposta
# instantânea, sem nenhuma chamada ao Zabbix (ver services/database.py).
CONFIGURACAO_BANCOS_POR_SISTEMA: dict[
    str, list[ConfiguracaoInstanciaBanco]
] = {
    "Portal Educação": [_MYSQL_PORTAL],
    "Portal CEU": [_MYSQL_PORTAL],
    "Intranet": [_MYSQL_PORTAL],
    "Rolê Agroecológico": [_MYSQL_PORTAL],
    "Plateia": [_POSTGRES_PADRAO],
    "Plateia App": [_POSTGRES_PADRAO],
    "SigPAE": [_POSTGRES_PADRAO],
    "Cdep": [_POSTGRES_PADRAO],
    "Currículo da Cidade": [_POSTGRES_PADRAO],
    "IDEP": [_POSTGRES_PADRAO],
    "Conecta Formação": [_POSTGRES_PADRAO],
    "SigEscola": [_POSTGRES_PADRAO],
    "GIPE": [_POSTGRES_PADRAO],
    "Sigla": [_POSTGRES_PADRAO],
    "Novo SGP": [
        ConfiguracaoInstanciaBanco(
            label="PostgreSQL (Escrita)",
            hostid="10747",
            key=_ITEM_KEY_PSQL_RUNNING,
            db_type="postgresql",
            role="escrita",
            avaliar_disponibilidade=avaliar_psql_running,
        ),
        ConfiguracaoInstanciaBanco(
            label="PostgreSQL (Leitura)",
            hostid="10745",
            key=_ITEM_KEY_PSQL_RUNNING,
            db_type="postgresql",
            role="leitura",
            avaliar_disponibilidade=avaliar_psql_running,
        ),
    ],
    "Serap Estudantes": [
        ConfiguracaoInstanciaBanco(
            label="PostgreSQL (Escrita)",
            hostid="10673",
            key=_ITEM_KEY_PSQL_RUNNING,
            db_type="postgresql",
            role="escrita",
            avaliar_disponibilidade=avaliar_psql_running,
        ),
        ConfiguracaoInstanciaBanco(
            label="PostgreSQL (Leitura)",
            hostid="10674",
            key=_ITEM_KEY_PSQL_RUNNING,
            db_type="postgresql",
            role="leitura",
            avaliar_disponibilidade=avaliar_psql_running,
        ),
    ],
    "Serap": [
        ConfiguracaoInstanciaBanco(
            label="SQL Server",
            hostid="10711",
            key='service.info["MSSQL$SME_PRD",state]',
            db_type="sqlserver",
            avaliar_disponibilidade=avaliar_sqlserver_running,
        ),
    ],
    "Escolhas": [],
}


def montar_parametros_trigger_producao(project: str, host: str) -> dict:
    """Monta os parâmetros de ``trigger.get`` do preset ``producao``.

    Args:
        project: Valor usado no filtro ``description`` do trigger.
        host: Valor usado no filtro ``host`` do trigger.

    Returns:
        Parâmetros prontos para ``client.zabbix_rpc("trigger.get")``.
    """
    return {
        "filter": {"host": [host], "description": [project]},
        "output": "extend",
    }


def montar_parametros_trigger_filas(project: str, host: str) -> dict:
    """Monta os parâmetros de ``trigger.get`` do preset ``filas``.

    Args:
        project: Valor usado no filtro ``description`` do trigger.
        host: Host consultado (usado diretamente, sem lista).

    Returns:
        Parâmetros prontos para ``client.zabbix_rpc("trigger.get")``.
    """
    return {
        "host": host,
        "output": "extend",
        "selectFunctions": "extend",
        "filter": {"description": project},
    }


PRESETS_STATUS: dict[str, Callable[[str, str], dict]] = {
    "producao": montar_parametros_trigger_producao,
    "filas": montar_parametros_trigger_filas,
}

HOSTIDS_JENKINS_PADRAO = "10726"
TIPO_ITEM_JENKINS = 18

# Ordem de tentativa fixa — o primeiro candidato encontrado ganha.
CANDIDATOS_HOMOLOG_FIXOS = [
    "homolog",
    "homologacao",
    "hml",
    "hmg",
    "develop",
    "dev",
    "staging",
    "stage",
]

REGEX_AMBIENTE_HOMOLOG = re.compile(
    r"^(homolog|homologacao|hml|hmg|develop|dev|staging|stage)$",
    re.IGNORECASE,
)
