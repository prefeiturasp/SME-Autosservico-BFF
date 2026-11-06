"""Views do app sgp.

As views não importam ``apps.sgp.client``: só leem o cache (via
``apps.core.cache``) e disparam a task de atualização em background quando
o cache está frio, devolvendo imediatamente o contrato de fallback.
"""

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import obter_ou_marcar_para_atualizar
from apps.sgp import fallback
from apps.sgp import tasks
from apps.sgp.api.serializers import MetricasSgpSerializer
from apps.sgp.api.serializers import PeriodosSgpSerializer
from apps.sgp.api.serializers import SgpFiltrosQuerySerializer
from apps.sgp.constants import CHAVE_CACHE_PERIODOS
from apps.sgp.constants import chave_cache_metricas


class MetricasSgpView(APIView):
    """Métricas do SGP, orquestradas a partir do backend (cache-aside).

    Lê o contrato já consolidado no cache, por ano letivo, segmento,
    semestre e bimestre. Quando o cache está frio, dispara
    ``tasks.atualizar_metricas`` em background e devolve imediatamente o
    contrato de fallback.
    """

    serializer_class = MetricasSgpSerializer

    @extend_schema(
        tags=["sgp"],
        summary="Métricas do SGP",
        operation_id="sgp_metricas",
        parameters=[SgpFiltrosQuerySerializer],
        responses=MetricasSgpSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o contrato de métricas do SGP para o período informado."""
        filtros = SgpFiltrosQuerySerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        periodo = (
            filtros.validated_data["ano_letivo"],
            filtros.validated_data["segmento"],
            filtros.validated_data["semestre"],
            filtros.validated_data["bimestre"],
        )

        payload = obter_ou_marcar_para_atualizar(
            chave_cache_metricas(*periodo),
            tasks.atualizar_metricas,
            periodo,
            ttl_lock=settings.SGP_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = fallback.metricas_indisponivel(*periodo)

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class PeriodosSgpView(APIView):
    """Opções do filtro de período do SGP."""

    serializer_class = PeriodosSgpSerializer

    @extend_schema(
        tags=["sgp"],
        summary="Períodos do filtro de métricas do SGP",
        operation_id="sgp_periodos",
        responses=PeriodosSgpSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna os bimestres já iniciados."""
        payload = obter_ou_marcar_para_atualizar(
            CHAVE_CACHE_PERIODOS,
            tasks.atualizar_periodos,
            (),
            ttl_lock=settings.SGP_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = fallback.periodos_indisponivel()

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
