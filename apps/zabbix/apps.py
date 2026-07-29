"""Configuração do app zabbix."""

from django.apps import AppConfig


class ZabbixConfig(AppConfig):
    """Comunicação com o Zabbix: disponibilidade, banco de dados e builds."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.zabbix"
    verbose_name = "Zabbix"
