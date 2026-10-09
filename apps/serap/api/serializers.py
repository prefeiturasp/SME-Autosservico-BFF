"""Serializers da API do app serap.

Refletem o contrato de métricas servido pelo backend do autosserviço. O
BFF apenas orquestra/cacheia esse contrato — os campos e nomes seguem os
do backend.
"""

from rest_framework import serializers


class SerapComAcessoAtivoSerializer(serializers.Serializer):
    """Usuários com acesso ativo e a variação nos últimos 30 dias."""

    valor = serializers.IntegerField()
    variacao_30_dias = serializers.IntegerField()


class SerapUsuariosSerializer(serializers.Serializer):
    """Bloco de métricas de usuários do SERAp Estudantes."""

    com_acesso_ativo = SerapComAcessoAtivoSerializer(allow_null=True)
    unicos_por_dia = serializers.IntegerField(allow_null=True)
    acessos_por_hora = serializers.IntegerField(allow_null=True)


class SerapProvasSerializer(serializers.Serializer):
    """Indicadores do painel de provas do SERAp."""

    total = serializers.IntegerField(allow_null=True)
    iniciadas_hoje = serializers.IntegerField(allow_null=True)
    nao_finalizadas = serializers.IntegerField(allow_null=True)
    finalizadas = serializers.IntegerField(allow_null=True)
    percentual_finalizadas = serializers.FloatField(allow_null=True)


class MetricasSerapSerializer(serializers.Serializer):
    """Contrato de métricas do SERAp servido pelo BFF."""

    atualizado_em = serializers.CharField(allow_null=True)
    ano = serializers.IntegerField()
    bimestre = serializers.IntegerField()
    usuarios = SerapUsuariosSerializer(allow_null=True)
    provas = SerapProvasSerializer(allow_null=True)
