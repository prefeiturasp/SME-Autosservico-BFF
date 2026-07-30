"""Leitura somente-leitura de bancos PostgreSQL de sistemas externos.

Infraestrutura genérica reaproveitável por qualquer domínio que precise
ler (nunca escrever) dados relacionais de um sistema legado da SME —
ver POC ``POC-Metricas-SGP`` (Spassu). Não usa ORM/migrations: quem
chama já traz a connection string e o SQL prontos.

Só deve ser chamado a partir de uma Celery task, nunca da camada de
request síncrona — mesma regra dos demais clientes de infraestrutura
(``apps/core/client_kibana.py``, ``apps/zabbix/client.py``): o resultado
deve ser guardado em cache pela task, e a view só lê o cache.
"""

from typing import Any

import psycopg
from psycopg.rows import dict_row


def executar_consulta_leitura(
    connection_string: str,
    query: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    """Executa uma consulta SQL somente-leitura num banco externo.

    Args:
        connection_string: String de conexão (host, banco, credenciais
            de um usuário com permissão apenas de ``SELECT``).
        query: Consulta SQL a executar.
        params: Parâmetros posicionais da consulta, se houver.

    Returns:
        As linhas retornadas, cada uma como um dicionário
        coluna→valor.
    """
    with (
        psycopg.connect(connection_string, row_factory=dict_row) as conexao,
        conexao.cursor() as cursor,
    ):
        cursor.execute(query, params)
        return cursor.fetchall()
