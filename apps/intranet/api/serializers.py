"""Serializers da API do app intranet (mesmo contrato do backend)."""

from rest_framework import serializers


class KpiIntranetSerializer(serializers.Serializer):
    """KPI de usuário (valor + tendência, hoje sempre nula)."""

    valor = serializers.IntegerField(allow_null=True)
    tendencia = serializers.FloatField(allow_null=True)
    tendencia_label = serializers.CharField(allow_null=True)


class KpisIntranetSerializer(serializers.Serializer):
    """Bloco de KPIs de usuário do Intranet."""

    acesso_ativo = KpiIntranetSerializer()
    usuarios_unicos = KpiIntranetSerializer()
    acessos_hoje = KpiIntranetSerializer()


class ItemContagemSerializer(serializers.Serializer):
    """Item de um card de distribuição (rótulo + total)."""

    # Conflita com ``Field.label`` só na tipagem; o nome vem do backend.
    label = serializers.CharField()  # type: ignore[assignment]
    value = serializers.IntegerField()


class StatusSorteiosSerializer(serializers.Serializer):
    """Status geral dos Sorteios."""

    cadastrados = serializers.IntegerField()
    realizados = serializers.IntegerField()
    ativos = serializers.IntegerField()
    encerrados = serializers.IntegerField()


class StatusOrdemInscricaoSerializer(serializers.Serializer):
    """Status geral de Ordem de Inscrição (sem "realizados")."""

    cadastrados = serializers.IntegerField()
    ativos = serializers.IntegerField()
    encerrados = serializers.IntegerField()


class SorteiosSerializer(serializers.Serializer):
    """Bloco de Sorteios."""

    status_geral = StatusSorteiosSerializer()
    por_tipo = ItemContagemSerializer(many=True)
    por_ganhador = ItemContagemSerializer(many=True)
    por_dre = ItemContagemSerializer(many=True)


class OrdemInscricaoSerializer(serializers.Serializer):
    """Bloco de Ordem de Inscrição."""

    status_geral = StatusOrdemInscricaoSerializer()
    por_tipo = ItemContagemSerializer(many=True)
    por_ganhador = ItemContagemSerializer(many=True)
    por_dre = ItemContagemSerializer(many=True)


class OportunidadesSerializer(serializers.Serializer):
    """Bloco de Oportunidades e Recrutamento."""

    cadastradas = serializers.IntegerField()
    cvs_cadastrados = serializers.IntegerField()
    inscricoes_realizadas = serializers.IntegerField()
    contratacoes_efetivadas = serializers.IntegerField()


class MetricasIntranetSerializer(serializers.Serializer):
    """Contrato de métricas do Intranet servido pelo BFF."""

    atualizado_em = serializers.CharField(allow_null=True)
    periodo = serializers.CharField()
    mes = serializers.CharField(allow_null=True)
    kpis = KpisIntranetSerializer(allow_null=True)
    sorteios = SorteiosSerializer(allow_null=True)
    ordem_inscricao = OrdemInscricaoSerializer(allow_null=True)
    oportunidades = OportunidadesSerializer(allow_null=True)
