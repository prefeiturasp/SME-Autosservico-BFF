"""Serializers da API do app sgp.

Refletem o contrato de métricas servido pelo backend do autosserviço. O
BFF apenas orquestra/cacheia esse contrato — os campos e nomes seguem os
do backend.
"""

from typing import Any

from rest_framework import serializers

from apps.sgp.constants import BIMESTRES_POR_SEGMENTO
from apps.sgp.constants import SEGMENTO_EJA
from apps.sgp.constants import SEGMENTO_FUNDAMENTAL_MEDIO
from apps.sgp.constants import SEGMENTOS


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


class FechamentoDreSerializer(serializers.Serializer):
    """Fechamento de uma DRE, por situação."""

    dre = serializers.CharField()
    previsto = serializers.IntegerField()
    nao_iniciados = serializers.IntegerField()
    processado_sucesso = serializers.IntegerField()
    processado_pendencias = serializers.IntegerField()
    processado_erro = serializers.IntegerField()


class FechamentoSerializer(serializers.Serializer):
    """Acompanhamento de fechamento por situação, geral e por DRE."""

    esperado = serializers.IntegerField(allow_null=True)
    nao_iniciados = serializers.IntegerField(allow_null=True)
    processado_sucesso = serializers.IntegerField(allow_null=True)
    processado_pendencias = serializers.IntegerField(allow_null=True)
    processado_erro = serializers.IntegerField(allow_null=True)
    por_dre = FechamentoDreSerializer(many=True)


class ConselhoClasseDreSerializer(serializers.Serializer):
    """Conselho de classe de uma DRE, por situação."""

    dre = serializers.CharField()
    previsto = serializers.IntegerField()
    nao_iniciados = serializers.IntegerField()
    em_andamento = serializers.IntegerField()
    processado_sucesso = serializers.IntegerField()


class ConselhoClasseSerializer(serializers.Serializer):
    """Conselho de classe por situação, geral e por DRE."""

    esperado = serializers.IntegerField(allow_null=True)
    nao_iniciados = serializers.IntegerField(allow_null=True)
    em_andamento = serializers.IntegerField(allow_null=True)
    processado_sucesso = serializers.IntegerField(allow_null=True)
    por_dre = ConselhoClasseDreSerializer(many=True)


class PeriodoSerializer(serializers.Serializer):
    """Período consultado."""

    ano_letivo = serializers.IntegerField()
    segmento = serializers.ChoiceField(choices=SEGMENTOS)
    semestre = serializers.IntegerField(allow_null=True)
    bimestre = serializers.IntegerField()


class SgpFiltrosQuerySerializer(serializers.Serializer):
    """Filtros das métricas do SGP, com as mesmas regras do backend."""

    ano_letivo = serializers.IntegerField(min_value=2000, max_value=2100)
    bimestre = serializers.IntegerField(min_value=1, max_value=4)
    segmento = serializers.ChoiceField(
        choices=SEGMENTOS, default=SEGMENTO_FUNDAMENTAL_MEDIO
    )
    semestre = serializers.IntegerField(
        min_value=1, max_value=2, required=False, allow_null=True
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Exige semestre na EJA e limita o bimestre ao segmento."""
        segmento = attrs["segmento"]
        if segmento == SEGMENTO_EJA and not attrs.get("semestre"):
            raise serializers.ValidationError(
                {"semestre": ["Obrigatório para a EJA."]}
            )
        if segmento != SEGMENTO_EJA:
            attrs["semestre"] = None
        maximo = BIMESTRES_POR_SEGMENTO[segmento]
        if attrs["bimestre"] > maximo:
            raise serializers.ValidationError(
                {"bimestre": [f"Deve estar entre 1 e {maximo}."]}
            )
        return attrs


class MetricasSgpSerializer(serializers.Serializer):
    """Contrato de métricas do SGP servido pelo BFF."""

    atualizado_em = serializers.CharField(allow_null=True)
    ano_letivo = serializers.IntegerField()
    bimestre = serializers.IntegerField()
    periodo = PeriodoSerializer()
    usuarios = SgpUsuariosSerializer(allow_null=True)
    frequencias = FrequenciasSerializer(allow_null=True)
    sondagens = SondagensSerializer(allow_null=True)
    fechamento = FechamentoSerializer(allow_null=True)
    conselho_classe = ConselhoClasseSerializer(allow_null=True)


class PeriodoOpcaoSerializer(serializers.Serializer):
    """Opção do filtro de período."""

    ano_letivo = serializers.IntegerField()
    segmento = serializers.ChoiceField(choices=SEGMENTOS)
    semestre = serializers.IntegerField(allow_null=True)
    bimestre = serializers.IntegerField()
    inicio = serializers.DateField()
    fim = serializers.DateField()


class PeriodosSgpSerializer(serializers.Serializer):
    """Opções do filtro de período do SGP."""

    periodos = PeriodoOpcaoSerializer(many=True, allow_null=True)
