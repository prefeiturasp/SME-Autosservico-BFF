"""Serializers da API do app bensfisicos."""

from rest_framework import serializers


class BensFisicosValorSerializer(serializers.Serializer):
    """Indicador de valor único."""

    valor = serializers.IntegerField()


class BensFisicosUnicosPorDiaSerializer(serializers.Serializer):
    """Usuários únicos hoje e a variação sobre a média de 30 dias."""

    valor = serializers.IntegerField()
    variacao_percentual_30_dias = serializers.FloatField(allow_null=True)


class BensFisicosUsuariosSerializer(serializers.Serializer):
    """Bloco de usuários do Bens Físicos."""

    com_acesso_ativo = BensFisicosValorSerializer()
    unicos_por_dia = BensFisicosUnicosPorDiaSerializer()


class BensFisicosUnidadeSerializer(serializers.Serializer):
    """Bens cadastrados de uma unidade administrativa."""

    sigla = serializers.CharField()
    nome = serializers.CharField()
    bens = serializers.IntegerField()


class BensFisicosCadastroSerializer(serializers.Serializer):
    """Bloco de cadastro de bens."""

    bens_cadastrados = serializers.IntegerField()
    aguardando_aprovacao = serializers.IntegerField()
    por_unidade_administrativa = BensFisicosUnidadeSerializer(many=True)


class BensFisicosBaixasSerializer(serializers.Serializer):
    """Bloco de baixas físicas (por pedido)."""

    aprovadas = serializers.IntegerField()
    aguardando_aprovacao = serializers.IntegerField()


class BensFisicosMovimentacoesSerializer(serializers.Serializer):
    """Bloco de movimentações e transferências (por pedido)."""

    realizadas = serializers.IntegerField()
    pendentes = serializers.IntegerField()
    transferencias_realizadas = serializers.IntegerField()


class MetricasBensFisicosSerializer(serializers.Serializer):
    """Contrato de métricas do Bens Físicos servido pelo BFF."""

    atualizado_em = serializers.CharField(allow_null=True)
    usuarios = BensFisicosUsuariosSerializer(allow_null=True)
    cadastro_de_bens = BensFisicosCadastroSerializer(allow_null=True)
    baixas_fisicas = BensFisicosBaixasSerializer(allow_null=True)
    movimentacoes = BensFisicosMovimentacoesSerializer(allow_null=True)
