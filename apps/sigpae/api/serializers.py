"""Serializers da API do app sigpae.

Refletem o contrato de métricas servido pelo backend do autosserviço. O
BFF apenas orquestra/cacheia esse contrato — os campos e nomes seguem os
do backend.
"""

from rest_framework import serializers


class ComAcessoAtivoSerializer(serializers.Serializer):
    """Usuários com acesso ativo e novos nos últimos 30 dias."""

    total = serializers.IntegerField()
    ativos_30_dias = serializers.IntegerField()


class PorTipoPerfilSerializer(serializers.Serializer):
    """Total de usuários por visão de perfil."""

    codae = serializers.IntegerField(allow_null=True)
    dre = serializers.IntegerField(allow_null=True)
    ue = serializers.IntegerField(allow_null=True)
    empresa = serializers.IntegerField(allow_null=True)


class UsuariosSerializer(serializers.Serializer):
    """Bloco de métricas de usuários do SIGPAE."""

    com_acesso_ativo = ComAcessoAtivoSerializer(allow_null=True)
    unicos_por_dia = serializers.IntegerField(allow_null=True)
    acessos_hoje = serializers.IntegerField(allow_null=True)
    por_tipo_perfil = PorTipoPerfilSerializer()
    comparativo_acessos = serializers.JSONField(allow_null=True)


class MedicoesIniciaisSerializer(serializers.Serializer):
    """Funil de medições iniciais da alimentação terceirizada."""

    aguardando_envio_ue = serializers.IntegerField(allow_null=True)
    enviadas_pelas_unidades = serializers.IntegerField(allow_null=True)
    aprovadas_pelas_dres = serializers.IntegerField(allow_null=True)
    aguardando_codae = serializers.IntegerField(allow_null=True)
    aprovadas_codae = serializers.IntegerField(allow_null=True)


class AlimentacaoTerceirizadaSerializer(serializers.Serializer):
    """Bloco de métricas da alimentação terceirizada do SIGPAE."""

    medicoes_iniciais = MedicoesIniciaisSerializer()


class MetricasSigpaeSerializer(serializers.Serializer):
    """Contrato de métricas do SIGPAE servido pelo BFF."""

    atualizado_em = serializers.CharField(allow_null=True)
    usuarios = UsuariosSerializer()
    alimentacao_terceirizada = AlimentacaoTerceirizadaSerializer()
