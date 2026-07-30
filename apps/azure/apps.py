"""Configuração do app azure."""

from django.apps import AppConfig


class AzureConfig(AppConfig):
    """Comunicação com o Azure DevOps: backlog e métricas de bugs."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.azure"
    verbose_name = "Azure DevOps"
