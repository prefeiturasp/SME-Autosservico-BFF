"""Configuração do app sgp."""

from django.apps import AppConfig


class SgpConfig(AppConfig):
    """Orquestração das métricas do SGP servidas pelo backend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sgp"
    verbose_name = "SGP"
