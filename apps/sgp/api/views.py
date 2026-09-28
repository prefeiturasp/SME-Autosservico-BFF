"""Views do app sgp.

A view não importa ``apps.sgp.client`` — só lê o cache (via
``apps.core.cache``) e dispara a task de atualização em background quando
o cache está frio, devolvendo imediatamente o contrato de fallback.
"""

from typing import Any

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import obter_ou_marcar_para_atualizar
from apps.sgp import fallback
from apps.sgp import tasks
from apps.sgp.api.serializers import MetricasSgpSerializer
from apps.sgp.constants import chave_cache_metricas


def _param_int(request: Request, nome: str) -> int:
    """Lê e valida um parâmetro inteiro obrigatório da query string."""
    valor = request.query_params.get(nome)
    if valor is None:
        raise ValidationError({nome: "Parâmetro obrigatório."})
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ValidationError({nome: "Deve ser um inteiro."}) from exc


class MetricasSgpView(APIView):
    """Métricas do SGP, orquestradas a partir do backend (cache-aside).

    Lê o contrato já consolidado no cache, por ano letivo e bimestre.
    Quando o cache está frio, dispara ``tasks.atualizar_metricas`` em
    background e devolve imediatamente o contrato de fallback.
    """

    serializer_class = MetricasSgpSerializer

    @extend_schema(
        tags=["sgp"],
        summary="Métricas do SGP",
        operation_id="sgp_metricas",
        parameters=[
            OpenApiParameter(
                "ano_letivo", int, required=True, description="Ano letivo."
            ),
            OpenApiParameter(
                "bimestre", int, required=True, description="Bimestre."
            ),
        ],
        responses=MetricasSgpSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o contrato de métricas do SGP para o período informado."""
        ano_letivo = _param_int(request, "ano_letivo")
        bimestre = _param_int(request, "bimestre")

        payload = obter_ou_marcar_para_atualizar(
            chave_cache_metricas(ano_letivo, bimestre),
            tasks.atualizar_metricas,
            (ano_letivo, bimestre),
            ttl_lock=settings.SGP_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = fallback.metricas_indisponivel(ano_letivo, bimestre)

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
