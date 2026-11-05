"""Serializers da API do app gipe.

Refletem o contrato de métricas servido pelo backend do autosserviço. O
BFF apenas orquestra/cacheia esse contrato — os campos e nomes seguem os
do backend. ``GipeFiltrosQuerySerializer`` valida a query string antes de
ela virar chave de cache.
"""

from rest_framework import serializers


class GipeFiltrosQuerySerializer(serializers.Serializer):
    """Filtros da query string.

    ``ano_letivo`` é opcional: sem ele, vale o ano letivo corrente.
    """

    ano_letivo = serializers.IntegerField(
        min_value=2000, max_value=2100, required=False
    )


class GipeKpiSerializer(serializers.Serializer):
    """KPI de usuário (valor + tendência)."""

    valor = serializers.IntegerField()
    tendencia = serializers.CharField(allow_null=True)
    tendencia_label = serializers.CharField(allow_null=True)


class GipeKpisSerializer(serializers.Serializer):
    """Bloco de KPIs de usuário do GIPE."""

    acesso_ativo = GipeKpiSerializer()
    usuarios_unicos = GipeKpiSerializer()
    acessos_hoje = GipeKpiSerializer()


class GipeItemContagemSerializer(serializers.Serializer):
    """Item de um card de distribuição (rótulo + total)."""

    # ``label`` sombreia ``Field.label`` só na tipagem: em runtime o DRF
    # trata campos declarados. O nome vem do contrato com o BFF.
    label = serializers.CharField()  # type: ignore[assignment]
    value = serializers.IntegerField()


class GipeItemPercentualSerializer(serializers.Serializer):
    """Item de um card em percentual (rótulo + percentual inteiro)."""

    label = serializers.CharField()  # type: ignore[assignment]
    percentage = serializers.IntegerField()


class GipeItemMesSerializer(serializers.Serializer):
    """Mês da série de ocorrências, com o destaque do pico."""

    label = serializers.CharField()  # type: ignore[assignment]
    valor = serializers.IntegerField()
    pico = serializers.BooleanField()


class GipeAnalistaSerializer(serializers.Serializer):
    """Ocorrências tratadas por um analista do GIPE."""

    analista = serializers.CharField()
    ocorrencias_tratadas = serializers.IntegerField()
    tempo_medio = serializers.CharField()


class GipeStatusGeralSerializer(serializers.Serializer):
    """Status geral das ocorrências."""

    cadastrados = serializers.IntegerField()
    abertas = serializers.IntegerField()
    em_andamento = serializers.IntegerField()
    finalizadas = serializers.IntegerField()


class GipeTempoRespostaSerializer(serializers.Serializer):
    """Tempos médios (em dias) de resolução e de primeira tratativa."""

    tempo_medio_resolucao_dias = serializers.FloatField(allow_null=True)
    tendencia_resolucao = serializers.CharField(allow_null=True)
    tendencia_resolucao_label = serializers.CharField(allow_null=True)
    tempo_medio_primeira_tratativa_dias = serializers.FloatField(
        allow_null=True
    )
    tendencia_primeira_tratativa = serializers.CharField(allow_null=True)
    tendencia_primeira_tratativa_label = serializers.CharField(allow_null=True)


class GipePrazosSerializer(serializers.Serializer):
    """Prazos e movimentações (dentro/fora do prazo sem fonte: nulos)."""

    dentro_do_prazo = serializers.IntegerField(allow_null=True)
    fora_do_prazo = serializers.IntegerField(allow_null=True)
    sem_movimentacao_7_dias = serializers.IntegerField()
    media_movimentacoes_por_ocorrencia = serializers.FloatField(
        allow_null=True
    )


class GipeCategoriaSerializer(serializers.Serializer):
    """Ocorrências patrimoniais x interpessoais."""

    patrimoniais = serializers.IntegerField()
    interpessoais = serializers.IntegerField()


class GipeOcorrenciasSerializer(serializers.Serializer):
    """Bloco de ocorrências do GIPE."""

    status_geral = GipeStatusGeralSerializer()
    tempo_resposta = GipeTempoRespostaSerializer()
    prazos_movimentacoes = GipePrazosSerializer()
    por_dre = GipeItemContagemSerializer(many=True)
    por_unidade_educacional = GipeItemContagemSerializer(many=True)
    por_categoria = GipeCategoriaSerializer()
    por_tipo_patrimonial = GipeItemContagemSerializer(many=True)
    por_tipo_interpessoal = GipeItemContagemSerializer(many=True)
    por_mes = GipeItemMesSerializer(many=True)
    por_periodo_letivo = GipeItemContagemSerializer(many=True)
    tratadas_por_analista = GipeAnalistaSerializer(many=True)
    tratadas_por_dre = GipeItemContagemSerializer(many=True)


class GipeUsuariosSerializer(serializers.Serializer):
    """Bloco de usuários do GIPE."""

    cadastrados = serializers.IntegerField()
    por_tipo_de_perfil = GipeItemPercentualSerializer(many=True)
    perfis_mais_utilizados = GipeItemContagemSerializer(many=True)
    por_dre = GipeItemContagemSerializer(many=True)
    por_unidade_educacional = GipeItemContagemSerializer(many=True)


class GipeProdutividadeSerializer(serializers.Serializer):
    """Bloco de produtividade do GIPE."""

    encaminhamentos_realizados = serializers.IntegerField()
    anexos_enviados = serializers.IntegerField()
    atualizacoes_nas_ocorrencias = serializers.IntegerField()


class MetricasGipeSerializer(serializers.Serializer):
    """Contrato de métricas do GIPE servido pelo BFF."""

    atualizado_em = serializers.CharField(allow_null=True)
    ano_letivo = serializers.IntegerField()
    kpis = GipeKpisSerializer(allow_null=True)
    ocorrencias = GipeOcorrenciasSerializer(allow_null=True)
    usuarios = GipeUsuariosSerializer(allow_null=True)
    produtividade = GipeProdutividadeSerializer(allow_null=True)
