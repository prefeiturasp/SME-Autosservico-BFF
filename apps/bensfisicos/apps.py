"""Configuração do app bensfisicos."""

from django.apps import AppConfig


class BensFisicosConfig(AppConfig):
    """Orquestração das métricas do Bens Físicos servidas pelo backend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bensfisicos"
    verbose_name = "Bens Físicos"
