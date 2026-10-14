"""Serializers da API do app zabbix.

Os campos seguem exatamente os nomes já usados pelo frontend
(``lastIncidentAt``, ``dbType``, ``hasDatabase``, ``timestampMs`` etc.)
Um contrato externo já fixado pelo ``SME-Autosservico-Frontend``,
não uma escolha de estilo Python (daí o ignore da regra ``N815`` do
ruff em ``pyproject.toml`` restrito a este arquivo). Campos opcionais
usam ``required=False`` sem ``default=``, para ficarem ausentes do
JSON de saída (não ``null``) quando não aplicável.
"""

from rest_framework import serializers


class ZabbixStatusSerializer(serializers.Serializer):
    """Status de disponibilidade (presets ``producao``/``filas``)."""

    available = serializers.BooleanField()
    incidents_recent = serializers.BooleanField()
    message = serializers.CharField()
    lastIncidentAt = serializers.CharField(required=False)


class SistemaDisponibilidadeSerializer(serializers.Serializer):
    """Descrições de disponibilidade (por ambiente) de um sistema."""

    sistema = serializers.CharField()
    producao = serializers.CharField()
    homologacao = serializers.CharField(required=False)


class DatabaseInstanceStatusSerializer(serializers.Serializer):
    """Status de uma instância de banco de dados."""

    label = serializers.CharField()  # type: ignore[assignment]
    dbType = serializers.CharField()
    available = serializers.BooleanField()
    role = serializers.CharField(required=False)


class DatabaseStatusSerializer(serializers.Serializer):
    """Status de banco de dados de um sistema."""

    system = serializers.CharField()
    hasDatabase = serializers.BooleanField()
    instances = DatabaseInstanceStatusSerializer(many=True)


class JenkinsBuildInfoSerializer(serializers.Serializer):
    """Informações compactas de um build do Jenkins."""

    number = serializers.IntegerField()
    status = serializers.CharField()
    timestampMs = serializers.FloatField()
    timestamp = serializers.CharField()
    durationMs = serializers.FloatField()
    duration = serializers.CharField()


class JenkinsJobSummarySerializer(serializers.Serializer):
    """Resumo de build de um job do Jenkins."""

    lastBuild = JenkinsBuildInfoSerializer(required=False)
    lastSuccessfulBuild = JenkinsBuildInfoSerializer(required=False)
    lastFailedBuild = JenkinsBuildInfoSerializer(required=False)
