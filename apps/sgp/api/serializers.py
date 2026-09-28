"""Serializers da API do app sgp.

Refletem o contrato de métricas servido pelo backend do autosserviço. O
BFF apenas orquestra/cacheia esse contrato — os campos e nomes seguem os
do backend.
"""

from rest_framework import serializers


class SgpComAcessoAtivoSerializer(serializers.Serializer):
    """Usuários com acesso ativo e a variação nos últimos 30 dias."""

    valor = serializers.IntegerField()
    variacao_30_dias = serializers.IntegerField()


class DeUnidadesEducacionaisSerializer(serializers.Serializer):
    """Usuários vinculados a unidades educacionais."""

    total = serializers.IntegerField()
    diretorias_regionais = serializers.IntegerField()


class SgpUsuariosSerializer(serializers.Serializer):
    """Bloco de métricas de usuários do SGP."""

    com_acesso_ativo = SgpComAcessoAtivoSerializer(allow_null=True)
    de_unidades_educacionais = DeUnidadesEducacionaisSerializer(
        allow_null=True
    )
    unicos_por_dia = serializers.IntegerField(allow_null=True)
    acessos_por_hora = serializers.IntegerField(allow_null=True)


class FrequenciasSerializer(serializers.Serializer):
    """Bloco de frequências lançadas/esperadas."""

    lancadas = serializers.IntegerField(allow_null=True)
    esperadas = serializers.IntegerField(allow_null=True)
    percentual = serializers.FloatField(allow_null=True)


class SondagensSerializer(serializers.Serializer):
    """Bloco de sondagens realizadas/esperadas."""

    realizadas = serializers.IntegerField(allow_null=True)
    esperadas = serializers.IntegerField(allow_null=True)


class FechamentoSerializer(serializers.Serializer):
    """Acompanhamento de fechamento por situação."""

    nao_iniciados = serializers.IntegerField(allow_null=True)
    processado_sucesso = serializers.IntegerField(allow_null=True)
    processado_pendencias = serializers.IntegerField(allow_null=True)
    processado_erro = serializers.IntegerField(allow_null=True)


class ConselhoClasseSerializer(serializers.Serializer):
    """Conselho de classe por situação."""

    nao_iniciados = serializers.IntegerField(allow_null=True)
    em_andamento = serializers.IntegerField(allow_null=True)
    processado_sucesso = serializers.IntegerField(allow_null=True)


class MetricasSgpSerializer(serializers.Serializer):
    """Contrato de métricas do SGP servido pelo BFF."""

    atualizado_em = serializers.CharField(allow_null=True)
    ano_letivo = serializers.IntegerField()
    bimestre = serializers.IntegerField()
    usuarios = SgpUsuariosSerializer(allow_null=True)
    frequencias = FrequenciasSerializer(allow_null=True)
    sondagens = SondagensSerializer(allow_null=True)
    fechamento = FechamentoSerializer(allow_null=True)
    conselho_classe = ConselhoClasseSerializer(allow_null=True)
