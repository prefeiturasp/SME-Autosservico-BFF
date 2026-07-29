"""Views do app zabbix.

Nenhuma view importa ``apps.zabbix.client`` nem os módulos de
``apps.zabbix.services`` que chamam o Zabbix de verdade — só
``apps.zabbix.cache`` (leitura do cache + disparo de Celery task em
background) e as funções de transformação pura dos services (usadas
só para montar o fallback seguro, sem nenhuma chamada de rede).
"""

from typing import Any

from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.zabbix import cache as zabbix_cache
from apps.zabbix import tasks
from apps.zabbix.api.serializers import DatabaseStatusSerializer
from apps.zabbix.api.serializers import JenkinsJobSummarySerializer
from apps.zabbix.api.serializers import ZabbixStatusSerializer
from apps.zabbix.constants import CONFIGURACAO_BANCOS_POR_SISTEMA
from apps.zabbix.constants import PRESETS_STATUS
from apps.zabbix.services.database import sistema_configurado
from apps.zabbix.services.status import status_a_partir_de_triggers


class StatusPresetView(APIView):
    """Status de disponibilidade (presets ``producao``/``filas``).

    Lê o cache de status já processado. Quando o cache está frio,
    dispara ``tasks.atualizar_status`` em background e devolve
    imediatamente o fallback seguro "sem incidentes conhecidos".
    """

    serializer_class = ZabbixStatusSerializer

    @extend_schema(
        tags=["zabbix"],
        summary="Status de disponibilidade (Zabbix)",
        operation_id="zabbix_status_preset",
        parameters=[
            OpenApiParameter(
                "preset",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                enum=list(PRESETS_STATUS),
            ),
            OpenApiParameter("project", OpenApiTypes.STR, required=True),
            OpenApiParameter("host", OpenApiTypes.STR, required=False),
        ],
        responses=ZabbixStatusSerializer,
    )
    def get(
        self, request: Request, preset: str, *args: Any, **kwargs: Any
    ) -> Response:
        """Retorna o status de disponibilidade para o preset informado.

        Returns:
            Response: status de disponibilidade, ou 400 se `project`
            estiver ausente ou o preset for desconhecido.
        """
        preset = preset.lower()
        project = request.query_params.get("project", "").strip()
        host = (
            request.query_params.get("host", "").strip()
            or settings.ZABBIX_DEFAULT_HOST
        )

        if not project:
            return Response(
                {"error": "project é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if preset not in PRESETS_STATUS:
            return Response(
                {"error": "preset inválido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chave = zabbix_cache.chave_status(preset, host, project)
        payload = zabbix_cache.obter_ou_marcar_para_atualizar(
            chave,
            tasks.atualizar_status,
            (preset, host, project),
            ttl_lock=settings.ZABBIX_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = status_a_partir_de_triggers([])

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class DatabaseStatusView(APIView):
    """Status de banco de dados de um sistema, via item.get do Zabbix.

    Sistemas sem instância configurada respondem instantaneamente, sem
    tocar cache nem disparar nenhuma Celery task.
    """

    serializer_class = DatabaseStatusSerializer

    @extend_schema(
        tags=["zabbix"],
        summary="Status de banco de dados (Zabbix)",
        operation_id="zabbix_database_status",
        parameters=[
            OpenApiParameter("system", OpenApiTypes.STR, required=True),
        ],
        responses=DatabaseStatusSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o status de banco de dados do sistema informado.

        Returns:
            Response: status de banco de dados, ou 400 se `system`
            estiver ausente.
        """
        sistema = request.query_params.get("system", "").strip()
        if not sistema:
            return Response(
                {"error": "system é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not sistema_configurado(sistema):
            payload_sem_banco = {
                "system": sistema,
                "hasDatabase": False,
                "instances": [],
            }
            serializer = self.serializer_class(data=payload_sem_banco)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data)

        chave = zabbix_cache.chave_database(sistema)
        payload: dict[str, Any] | None = (
            zabbix_cache.obter_ou_marcar_para_atualizar(
                chave,
                tasks.atualizar_status_banco_sistema,
                (sistema,),
                ttl_lock=settings.ZABBIX_LOCK_TTL_SECONDS,
            )
        )
        if payload is None:
            payload = {
                "system": sistema,
                "hasDatabase": True,
                "instances": [
                    {
                        "label": cfg.label,
                        "dbType": cfg.db_type,
                        "available": False,
                        **({"role": cfg.role} if cfg.role else {}),
                    }
                    for cfg in CONFIGURACAO_BANCOS_POR_SISTEMA[sistema]
                ],
            }

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class JenkinsJobSummaryView(APIView):
    """Resumo de build do Jenkins, lido via item.get do Zabbix.

    Lê o cache do resumo já processado. Quando o cache está frio,
    dispara ``tasks.atualizar_jenkins_job`` em background e devolve
    imediatamente um resumo vazio.
    """

    serializer_class = JenkinsJobSummarySerializer

    @extend_schema(
        tags=["zabbix"],
        summary="Resumo de build do Jenkins (via Zabbix)",
        operation_id="zabbix_jenkins_job_summary",
        parameters=[
            OpenApiParameter("project", OpenApiTypes.STR, required=True),
            OpenApiParameter(
                "env",
                OpenApiTypes.STR,
                required=False,
                enum=["prod", "homolog"],
            ),
        ],
        responses=JenkinsJobSummarySerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o resumo de build do Jenkins para o projeto informado.

        Returns:
            Response: resumo de build, ou 400 se `project` estiver
            ausente.
        """
        project = request.query_params.get("project", "").strip()
        ambiente = (
            "homolog"
            if request.query_params.get("env", "").strip().lower() == "homolog"
            else "prod"
        )

        if not project:
            return Response(
                {"error": "project é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chave = zabbix_cache.chave_jenkins(project, ambiente)
        payload = zabbix_cache.obter_ou_marcar_para_atualizar(
            chave,
            tasks.atualizar_jenkins_job,
            (project, ambiente),
            ttl_lock=settings.ZABBIX_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = {}

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
