"""Serializers do app core."""

from rest_framework import serializers


class HealthCheckSerializer(serializers.Serializer):
    """Representa o payload retornado pelo endpoint de health check."""

    status = serializers.CharField(help_text="Status geral do serviço.")
