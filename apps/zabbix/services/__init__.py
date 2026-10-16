"""Camada de serviço: regras de negócio da integração com o Zabbix.

Cada submódulo cobre um domínio (status de disponibilidade, banco de
dados, resumo de build do Jenkins). As funções que chamam o Zabbix de
verdade (``obter_status``, ``obter_status_banco``, ``obter_resumo``) só
devem ser chamadas a partir de ``apps/zabbix/tasks.py`` — as funções de
transformação pura (ex.: ``status.status_a_partir_de_triggers``) podem
ser reaproveitadas pelas views para montar o fallback seguro sem
nenhuma chamada ao Zabbix.
"""
