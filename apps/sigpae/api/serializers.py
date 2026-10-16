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
    novos_30_dias = serializers.IntegerField()


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


class ProdutosHomologadosSerializer(serializers.Serializer):
    """Indicadores de produtos homologados da alimentação terceirizada."""

    total_cadastrados = serializers.IntegerField(allow_null=True)
    homologados = serializers.IntegerField(allow_null=True)
    solicitacoes_no_mes = serializers.IntegerField(allow_null=True)
    solicitacoes_no_ano = serializers.IntegerField(allow_null=True)


class EmpresasTerceirizadasSerializer(serializers.Serializer):
    """Empresas terceirizadas cadastradas e ativas."""

    cadastradas = serializers.IntegerField(allow_null=True)
    ativas = serializers.IntegerField(allow_null=True)


class SolicitacaoStatusSerializer(serializers.Serializer):
    """Contagens de uma solicitação por status, num período."""

    total = serializers.IntegerField(allow_null=True)
    autorizadas = serializers.IntegerField(allow_null=True)
    aguardando = serializers.IntegerField(allow_null=True)
    negadas = serializers.IntegerField(allow_null=True)
    canceladas = serializers.IntegerField(allow_null=True)


class SolicitacoesPorPeriodoSerializer(serializers.Serializer):
    """Solicitações agregadas nos 4 períodos do seletor."""

    dia = SolicitacaoStatusSerializer(allow_null=True)
    quinzena = SolicitacaoStatusSerializer(allow_null=True)
    mes = SolicitacaoStatusSerializer(allow_null=True)
    trimestre = SolicitacaoStatusSerializer(allow_null=True)


class AlimentacaoTerceirizadaSerializer(serializers.Serializer):
    """Bloco de métricas da alimentação terceirizada do SIGPAE."""

    medicoes_iniciais = MedicoesIniciaisSerializer()
    produtos_homologados = ProdutosHomologadosSerializer(allow_null=True)
    empresas_terceirizadas = EmpresasTerceirizadasSerializer(allow_null=True)
    solicitacoes_dietas_especiais = SolicitacoesPorPeriodoSerializer(
        allow_null=True
    )
    solicitacoes_alimentacoes = SolicitacoesPorPeriodoSerializer(
        allow_null=True
    )


class CronogramasEntregasSerializer(serializers.Serializer):
    """Cronogramas de entregas por etapa do fluxo."""

    aguardando = serializers.IntegerField(allow_null=True)
    enviadas = serializers.IntegerField(allow_null=True)
    aprovadas = serializers.IntegerField(allow_null=True)


class FichasTecnicasProdutosSerializer(serializers.Serializer):
    """Fichas técnicas de produtos por status."""

    cadastradas = serializers.IntegerField(allow_null=True)
    aprovadas = serializers.IntegerField(allow_null=True)
    em_analise = serializers.IntegerField(allow_null=True)
    pendentes_correcao = serializers.IntegerField(allow_null=True)


class LayoutsEmbalagensSerializer(serializers.Serializer):
    """Layouts de embalagens por status."""

    cadastrados = serializers.IntegerField(allow_null=True)
    aprovados = serializers.IntegerField(allow_null=True)
    aguardando_codae = serializers.IntegerField(allow_null=True)
    pendentes_correcao = serializers.IntegerField(allow_null=True)


class FornecedoresDistribuidoresSerializer(serializers.Serializer):
    """Fornecedores e distribuidores cadastrados e ativos."""

    cadastradas = serializers.IntegerField(allow_null=True)
    ativas = serializers.IntegerField(allow_null=True)


class LogisticaSerializer(serializers.Serializer):
    """Bloco de métricas de logística (pré-recebimento) do SIGPAE."""

    cronogramas_entregas = CronogramasEntregasSerializer(allow_null=True)
    fichas_tecnicas_produtos = FichasTecnicasProdutosSerializer(
        allow_null=True
    )
    fornecedores_distribuidores = FornecedoresDistribuidoresSerializer(
        allow_null=True
    )
    layouts_embalagens = LayoutsEmbalagensSerializer(allow_null=True)


class MetricasSigpaeSerializer(serializers.Serializer):
    """Contrato de métricas do SIGPAE servido pelo BFF."""

    atualizado_em = serializers.CharField(allow_null=True)
    usuarios = UsuariosSerializer()
    alimentacao_terceirizada = AlimentacaoTerceirizadaSerializer()
    logistica = LogisticaSerializer()
