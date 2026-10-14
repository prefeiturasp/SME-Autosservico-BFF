"""Configuração do app sigescola."""

from django.apps import AppConfig


class SigescolaConfig(AppConfig):
    """Orquestração das métricas do SIG-Escola servidas pelo backend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sigescola"
    verbose_name = "SIG-Escola"
