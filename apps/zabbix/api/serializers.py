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

from apps.zabbix.constants import GRANULARIDADES_SERIE_ACESSOS


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


class ConectadosSerializer(serializers.Serializer):
    """Conexões no hub do SGP (o total inclui a fila)."""

    total = serializers.IntegerField(allow_null=True)
    sgp = serializers.IntegerField(allow_null=True)
    sondagem = serializers.IntegerField(allow_null=True)


class TempoEsperaEstimadoSerializer(serializers.Serializer):
    """Tempo de espera estimado pelo teste sintético de login."""

    media_s = serializers.FloatField(allow_null=True)
    posicao_media = serializers.IntegerField(allow_null=True)
    testes = serializers.IntegerField()
    atingiu_limite_teste = serializers.BooleanField()


class ControleAcessosSgpSerializer(serializers.Serializer):
    """Estado atual do controle de acessos do SGP."""

    atualizado_em = serializers.CharField(allow_null=True)
    limite_conexoes = serializers.IntegerField(allow_null=True)
    conectados = ConectadosSerializer(allow_null=True)
    em_fila = serializers.IntegerField(allow_null=True)
    fila_iniciada_em = serializers.CharField(allow_null=True)
    tempo_espera_estimado = TempoEsperaEstimadoSerializer(allow_null=True)


class SerieAcessosQuerySerializer(serializers.Serializer):
    """Filtro da série do gráfico de acessos."""

    granularidade = serializers.ChoiceField(
        choices=GRANULARIDADES_SERIE_ACESSOS
    )


class PontoSerieAcessosSerializer(serializers.Serializer):
    """Ponto do gráfico, com o pico de conectados e da fila."""

    inicio = serializers.CharField()
    total = serializers.IntegerField()
    em_fila_max = serializers.IntegerField()
    fila_ativa = serializers.BooleanField()


class SerieAcessosSgpSerializer(serializers.Serializer):
    """Série do gráfico "Acompanhamento de acessos" do SGP."""

    granularidade = serializers.ChoiceField(
        choices=GRANULARIDADES_SERIE_ACESSOS
    )
    atualizado_em = serializers.CharField(allow_null=True)
    pontos = PontoSerieAcessosSerializer(many=True)
