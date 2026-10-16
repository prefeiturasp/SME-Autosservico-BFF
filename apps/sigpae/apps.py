"""Configuração do app sigpae."""

from django.apps import AppConfig


class SigpaeConfig(AppConfig):
    """Orquestração das métricas do SIGPAE servidas pelo backend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sigpae"
    verbose_name = "SIGPAE"
