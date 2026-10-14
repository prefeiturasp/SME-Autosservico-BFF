"""Configuração do app intranet."""

from django.apps import AppConfig


class IntranetConfig(AppConfig):
    """Orquestração das métricas do Intranet servidas pelo backend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.intranet"
    verbose_name = "Intranet"
