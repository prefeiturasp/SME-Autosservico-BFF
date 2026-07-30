"""Views do app azure.

Nenhuma view importa ``apps.azure.client`` nem as funções de
``apps.azure.services`` que chamam o Azure de verdade — só
``apps.azure.cache`` (leitura do cache + disparo de Celery task em
background) e as funções puras do serviço, usadas apenas para montar o
fallback seguro e normalizar os filtros, sem nenhuma chamada de rede.
"""

from datetime import datetime
from typing import Any

from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.azure import cache as azure_cache
from apps.azure import tasks
from apps.azure.api.serializers import BacklogDiagnosticsSerializer
from apps.azure.api.serializers import BacklogRequestSerializer
from apps.azure.api.serializers import BacklogSerializer
from apps.azure.api.serializers import ProjectsListSerializer
from apps.azure.constants import CHAVES_FILTRO_LISTA
from apps.azure.constants import FILTRO_CONTAINS
from apps.azure.constants import FORMATO_DATA_ENTRADA
from apps.azure.constants import PROJETOS_TOP_MAXIMO
from apps.azure.constants import PROJETOS_TOP_MINIMO
from apps.azure.constants import PROJETOS_TOP_PADRAO
from apps.azure.constants import TTL_LOCK_SEGUNDOS
from apps.azure.services.backlog import montar_backlog_vazio
from apps.azure.services.backlog import normalizar_filtros
from apps.azure.services.backlog import normalizar_filtros_de_listas
from apps.azure.services.backlog import primeiro_e_ultimo_dia_do_mes
from apps.azure.services.diagnostico import montar_diagnostico_vazio
from apps.azure.services.projetos import montar_projetos_vazio

_ERRO_DATA = "Formato de data inválido. Use YYYY-MM-DD"
_ERRO_MES = "year e month devem formar um mês válido"
_ERRO_ORGANIZACAO = (
    "organization deve ser informado no request ou definido no ambiente"
)
_ERRO_PROJETO = "project_name é obrigatório"


def _erro(mensagem: str) -> Response:
    """Monta uma resposta 400 no formato de erro do BFF.

    Args:
        mensagem: Mensagem exibida ao chamador.

    Returns:
        Response: corpo ``{"error": ...}`` com HTTP 400.
    """
    return Response({"error": mensagem}, status=status.HTTP_400_BAD_REQUEST)


def _data_valida(valor: str) -> bool:
    """Indica se o texto está no formato ``YYYY-MM-DD``.

    Args:
        valor: Data recebida na requisição.

    Returns:
        ``True`` quando a data é válida.
    """
    try:
        datetime.strptime(valor, FORMATO_DATA_ENTRADA)
    except ValueError:
        return False
    return True


def _resolver_periodo(
    inicio: str, fim: str, ano: str, mes: str
) -> tuple[str | None, str | None, str | None]:
    """Resolve o período consultado a partir dos parâmetros recebidos.

    Aceita duas formas: ``start_date``/``end_date`` explícitos, ou
    ``year``/``month`` (que viram o primeiro e o último dia do mês).
    Sem nenhum dos dois, não há filtro de data.

    Args:
        inicio: Parâmetro ``start_date``.
        fim: Parâmetro ``end_date``.
        ano: Parâmetro ``year``.
        mes: Parâmetro ``month``.

    Returns:
        Tupla ``(inicio, fim, erro)`` — ``erro`` é ``None`` quando o
        período é válido.
    """
    if inicio and fim:
        if not (_data_valida(inicio) and _data_valida(fim)):
            return None, None, _ERRO_DATA
        return inicio, fim, None

    if ano and mes:
        try:
            primeiro, ultimo = primeiro_e_ultimo_dia_do_mes(int(ano), int(mes))
        except ValueError:
            return None, None, _ERRO_MES
        return primeiro, ultimo, None

    return None, None, None


def _resolver_organizacao(informada: str) -> str:
    """Resolve a organização a partir do request ou do ambiente.

    Args:
        informada: Organização recebida na requisição.

    Returns:
        A organização resolvida, ou string vazia se nenhuma existir.
    """
    return informada.strip() or str(settings.AZURE_DEVOPS_ORGANIZATION)


def _inteiro_no_intervalo(
    valor: str, padrao: int, minimo: int, maximo: int | None
) -> tuple[int, str | None]:
    """Converte um query param numérico, validando o intervalo.

    Args:
        valor: Texto recebido no query param.
        padrao: Valor usado quando o param está ausente.
        minimo: Menor valor aceito.
        maximo: Maior valor aceito, ou ``None`` se não houver teto.

    Returns:
        Tupla ``(numero, erro)`` — ``erro`` é ``None`` quando válido;
        quando há erro, o número devolvido é o padrão e é ignorado
        pelo chamador.
    """
    if not valor:
        return padrao, None
    try:
        numero = int(valor)
    except ValueError:
        return padrao, f"valor numérico inválido: {valor}"
    if numero < minimo or (maximo is not None and numero > maximo):
        limite = f"{minimo}-{maximo}" if maximo is not None else f">= {minimo}"
        return (
            padrao,
            f"valor fora do intervalo permitido ({limite}): {numero}",
        )
    return numero, None


class BacklogView(APIView):
    """Backlog de work items de um projeto do Azure DevOps.

    Lê o backlog já processado no cache. Quando o cache está frio,
    dispara ``tasks.atualizar_backlog`` em background e devolve
    imediatamente um backlog vazio — mesmo payload que o Azure produz
    quando a consulta não encontra work items, preservando o contrato
    consumido pelo frontend.

    Aceita ``GET`` (filtros em query params, separados por vírgula) e
    ``POST`` (filtros no corpo, já como listas). As duas formas
    resolvem para a mesma chave de cache quando equivalentes.
    """

    serializer_class = BacklogSerializer

    def _responder(
        self,
        organizacao: str,
        projeto: str,
        inicio: str | None,
        fim: str | None,
        filtros: dict[str, Any],
    ) -> Response:
        """Lê o cache do backlog e devolve a resposta já serializada.

        Args:
            organizacao: Organização resolvida.
            projeto: Nome do projeto consultado.
            inicio: Data inicial (``YYYY-MM-DD``) ou ``None``.
            fim: Data final (``YYYY-MM-DD``) ou ``None``.
            filtros: Filtros já normalizados.

        Returns:
            Response: backlog do projeto, com HTTP 200.
        """
        chave = azure_cache.chave_backlog(
            organizacao, projeto, inicio, fim, filtros
        )
        payload = azure_cache.obter_ou_marcar_para_atualizar(
            chave,
            tasks.atualizar_backlog,
            (organizacao, projeto, inicio, fim, filtros),
            ttl_lock=TTL_LOCK_SEGUNDOS,
        )
        if payload is None:
            payload = montar_backlog_vazio(organizacao, projeto, inicio, fim)

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

    @extend_schema(
        tags=["azure"],
        summary="Backlog de work items (Azure DevOps)",
        operation_id="azure_backlog",
        parameters=[
            OpenApiParameter("project_name", OpenApiTypes.STR, required=True),
            OpenApiParameter("organization", OpenApiTypes.STR),
            OpenApiParameter("start_date", OpenApiTypes.STR),
            OpenApiParameter("end_date", OpenApiTypes.STR),
            OpenApiParameter("year", OpenApiTypes.INT),
            OpenApiParameter("month", OpenApiTypes.INT),
            OpenApiParameter("work_item_types", OpenApiTypes.STR),
            OpenApiParameter("states", OpenApiTypes.STR),
            OpenApiParameter("area_paths", OpenApiTypes.STR),
            OpenApiParameter("iteration_paths", OpenApiTypes.STR),
            OpenApiParameter("assigned_to", OpenApiTypes.STR),
            OpenApiParameter("tags", OpenApiTypes.STR),
        ],
        responses=BacklogSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o backlog do projeto informado via query params.

        Returns:
            Response: backlog do projeto, ou 400 quando `project_name`
            está ausente, a organização não foi resolvida ou o período
            informado é inválido.
        """
        projeto = request.query_params.get("project_name", "").strip()
        if not projeto:
            return _erro(_ERRO_PROJETO)

        organizacao = _resolver_organizacao(
            request.query_params.get("organization", "")
        )
        if not organizacao:
            return _erro(_ERRO_ORGANIZACAO)

        inicio, fim, erro = _resolver_periodo(
            request.query_params.get("start_date", "").strip(),
            request.query_params.get("end_date", "").strip(),
            request.query_params.get("year", "").strip(),
            request.query_params.get("month", "").strip(),
        )
        if erro:
            return _erro(erro)

        filtros = normalizar_filtros(
            {
                chave: request.query_params.get(chave, "")
                for chave in (*CHAVES_FILTRO_LISTA, FILTRO_CONTAINS)
            }
        )
        return self._responder(organizacao, projeto, inicio, fim, filtros)

    @extend_schema(
        tags=["azure"],
        summary="Backlog de work items, com filtros no corpo",
        operation_id="azure_backlog_post",
        request=BacklogRequestSerializer,
        responses=BacklogSerializer,
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o backlog do projeto informado no corpo da requisição.

        Returns:
            Response: backlog do projeto, ou 400 quando o corpo é
            inválido, a organização não foi resolvida ou o período
            informado é inválido.
        """
        entrada = BacklogRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data

        # project_name é obrigatório e não-vazio pelo serializer, que já
        # remove os espaços das pontas — aqui ele sempre chega válido.
        projeto = str(dados["project_name"])

        organizacao = _resolver_organizacao(dados.get("organization") or "")
        if not organizacao:
            return _erro(_ERRO_ORGANIZACAO)

        ano = dados.get("year")
        mes = dados.get("month")
        inicio, fim, erro = _resolver_periodo(
            (dados.get("start_date") or "").strip(),
            (dados.get("end_date") or "").strip(),
            str(ano) if ano else "",
            str(mes) if mes else "",
        )
        if erro:
            return _erro(erro)

        filtros = normalizar_filtros_de_listas(dados.get("filters") or {})
        return self._responder(organizacao, projeto, inicio, fim, filtros)


class BacklogDiagnosticsView(APIView):
    """Contagem de work items por tipo, para um projeto.

    Busca o backlog **sem filtro de tipo** e reporta quantos itens
    existem de cada ``System.WorkItemType``, com uma amostra dos
    primeiros. Serve para descobrir quais tipos um projeto usa antes de
    configurar os filtros do dashboard.
    """

    serializer_class = BacklogDiagnosticsSerializer

    @extend_schema(
        tags=["azure"],
        summary="Diagnóstico de tipos de work item (Azure DevOps)",
        operation_id="azure_backlog_diagnostics",
        parameters=[
            OpenApiParameter("project_name", OpenApiTypes.STR, required=True),
            OpenApiParameter("organization", OpenApiTypes.STR),
        ],
        responses=BacklogDiagnosticsSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o diagnóstico do projeto informado.

        Returns:
            Response: diagnóstico do projeto, ou 400 quando
            `project_name` está ausente ou a organização não foi
            resolvida.
        """
        projeto = request.query_params.get("project_name", "").strip()
        if not projeto:
            return _erro(_ERRO_PROJETO)

        organizacao = _resolver_organizacao(
            request.query_params.get("organization", "")
        )
        if not organizacao:
            return _erro(_ERRO_ORGANIZACAO)

        chave = azure_cache.chave_diagnostico(organizacao, projeto)
        payload = azure_cache.obter_ou_marcar_para_atualizar(
            chave,
            tasks.atualizar_diagnostico,
            (organizacao, projeto),
            ttl_lock=TTL_LOCK_SEGUNDOS,
        )
        if payload is None:
            payload = montar_diagnostico_vazio(projeto)

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class ProjectsView(APIView):
    """Listagem paginada dos projetos de uma organização."""

    serializer_class = ProjectsListSerializer

    @extend_schema(
        tags=["azure"],
        summary="Projetos da organização (Azure DevOps)",
        operation_id="azure_projects",
        parameters=[
            OpenApiParameter("organization", OpenApiTypes.STR),
            OpenApiParameter("top", OpenApiTypes.INT),
            OpenApiParameter("skip", OpenApiTypes.INT),
            OpenApiParameter("continuation_token", OpenApiTypes.STR),
        ],
        responses=ProjectsListSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna uma página de projetos da organização.

        Returns:
            Response: página de projetos, ou 400 quando a organização
            não foi resolvida ou a paginação é inválida.
        """
        organizacao = _resolver_organizacao(
            request.query_params.get("organization", "")
        )
        if not organizacao:
            return _erro(_ERRO_ORGANIZACAO)

        top, erro_top = _inteiro_no_intervalo(
            request.query_params.get("top", "").strip(),
            PROJETOS_TOP_PADRAO,
            PROJETOS_TOP_MINIMO,
            PROJETOS_TOP_MAXIMO,
        )
        if erro_top:
            return _erro(f"top: {erro_top}")

        skip, erro_skip = _inteiro_no_intervalo(
            request.query_params.get("skip", "").strip(), 0, 0, None
        )
        if erro_skip:
            return _erro(f"skip: {erro_skip}")

        token = (
            request.query_params.get("continuation_token", "").strip() or None
        )

        chave = azure_cache.chave_projetos(organizacao, top, skip, token)
        payload = azure_cache.obter_ou_marcar_para_atualizar(
            chave,
            tasks.atualizar_projetos,
            (organizacao, top, skip, token),
            ttl_lock=TTL_LOCK_SEGUNDOS,
        )
        if payload is None:
            payload = montar_projetos_vazio()

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
