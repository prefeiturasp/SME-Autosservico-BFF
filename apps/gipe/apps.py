"""Configuração do app gipe."""

from django.apps import AppConfig


class GipeConfig(AppConfig):
    """Orquestração das métricas do GIPE servidas pelo backend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gipe"
    verbose_name = "GIPE"
