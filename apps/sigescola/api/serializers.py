"""Serializers da API do app sigescola.

Refletem o contrato de métricas servido pelo backend do autosserviço. O
BFF apenas orquestra/cacheia esse contrato — os campos e nomes seguem os
do backend. ``SigEscolaFiltrosQuerySerializer`` valida a query string antes
de ela virar chave de cache.
"""

from typing import Any

from rest_framework import serializers

_CODIGO_EOL = r"^\d{6}$"


class SigEscolaFiltrosQuerySerializer(serializers.Serializer):
    """Filtros da query string, todos opcionais.

    Use ``periodo`` (referência do PTRF, ex.: ``2026.2``) ou o par
    ``data_inicio``/``data_fim``. Sem nenhum dos dois, vale o período
    corrente. ``dre`` e ``ue`` são códigos EOL.
    """

    periodo = serializers.RegexField(r"^\d{4}\.\d{1,2}$", required=False)
    data_inicio = serializers.DateField(required=False)
    data_fim = serializers.DateField(required=False)
    dre = serializers.RegexField(_CODIGO_EOL, required=False)
    ue = serializers.RegexField(_CODIGO_EOL, required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Exige o par de datas completo, em ordem e sem ``periodo``."""
        inicio = attrs.get("data_inicio")
        fim = attrs.get("data_fim")
        if (inicio is None) != (fim is None):
            raise serializers.ValidationError(
                "Informe data_inicio e data_fim juntas."
            )
        if inicio is not None and "periodo" in attrs:
            raise serializers.ValidationError(
                "Use periodo ou data_inicio/data_fim, não os dois."
            )
        if inicio is not None and inicio > fim:
            raise serializers.ValidationError(
                "data_inicio deve ser anterior ou igual a data_fim."
            )
        return attrs


class SigEscolaFiltrosAplicadosSerializer(serializers.Serializer):
    """Filtros aplicados: período resolvido, janela, DRE e UE."""

    periodo = serializers.CharField(allow_null=True)
    data_inicio = serializers.CharField(allow_null=True)
    data_fim = serializers.CharField(allow_null=True)
    dre = serializers.CharField(allow_null=True)
    ue = serializers.CharField(allow_null=True)


class SigEscolaUnidadeSerializer(serializers.Serializer):
    """UE oferecida no filtro (código EOL e rótulo)."""

    codigo_eol = serializers.CharField()
    nome = serializers.CharField()


class SigEscolaOpcoesSerializer(serializers.Serializer):
    """Opções reais dos filtros da tela."""

    periodos = serializers.ListField(child=serializers.CharField())
    unidades = SigEscolaUnidadeSerializer(many=True)


class SigEscolaComAcessoAtivoSerializer(serializers.Serializer):
    """Usuários que já logaram e os cadastrados nos últimos 30 dias."""

    valor = serializers.IntegerField()
    variacao_30_dias = serializers.IntegerField()


class SigEscolaHojeSobreAMediaSerializer(serializers.Serializer):
    """Valor de hoje e a variação (%) sobre a média diária de 30 dias."""

    valor = serializers.IntegerField()
    variacao_percentual_30_dias = serializers.FloatField()


class SigEscolaUsuariosSerializer(serializers.Serializer):
    """Bloco de métricas de usuários do SIG-Escola."""

    com_acesso_ativo = SigEscolaComAcessoAtivoSerializer(allow_null=True)
    unicos_por_dia = SigEscolaHojeSobreAMediaSerializer(allow_null=True)
    acessos_hoje = SigEscolaHojeSobreAMediaSerializer(allow_null=True)


class SigEscolaPlanoAnualSerializer(serializers.Serializer):
    """PAAs por situação."""

    em_andamento = serializers.IntegerField()
    finalizados = serializers.IntegerField()
    em_retificacao = serializers.IntegerField()


class SigEscolaPrestacaoDeContasSerializer(serializers.Serializer):
    """Indicadores do card de prestação de contas."""

    ues_aptas = serializers.IntegerField()
    enviadas_ou_em_andamento = serializers.IntegerField()
    creditos_disponiveis = serializers.FloatField()
    despesas_registradas = serializers.FloatField()
    demonstrativos_gerados = serializers.IntegerField()
    devolucao_ao_tesouro = serializers.FloatField()


class SigEscolaSituacaoPatrimonialSerializer(serializers.Serializer):
    """Bens de capital das UEs: quantidade e valor."""

    quantidade_bens_produzidos = serializers.IntegerField()
    valor_bens_produzidos = serializers.FloatField()


class MetricasSigEscolaSerializer(serializers.Serializer):
    """Contrato de métricas do SIG-Escola servido pelo BFF."""

    atualizado_em = serializers.CharField(allow_null=True)
    filtros = SigEscolaFiltrosAplicadosSerializer()
    opcoes = SigEscolaOpcoesSerializer(allow_null=True)
    usuarios = SigEscolaUsuariosSerializer(allow_null=True)
    plano_anual_de_atividades = SigEscolaPlanoAnualSerializer(allow_null=True)
    prestacao_de_contas = SigEscolaPrestacaoDeContasSerializer(allow_null=True)
    situacao_patrimonial = SigEscolaSituacaoPatrimonialSerializer(
        allow_null=True
    )
