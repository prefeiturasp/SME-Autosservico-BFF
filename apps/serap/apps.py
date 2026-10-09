"""Configuração do app serap."""

from django.apps import AppConfig


class SerapConfig(AppConfig):
    """Orquestração das métricas do SERAp servidas pelo backend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.serap"
    verbose_name = "SERAp"
