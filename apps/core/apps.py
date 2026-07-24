"""Configuração do app core."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Autenticação, health check e utilidades compartilhadas."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"
