"""Views do app serap.

A view não importa ``apps.serap.client`` — só lê o cache (via
``apps.core.cache``) e dispara a task de atualização em background quando
o cache está frio, devolvendo imediatamente o contrato de fallback.
"""

from typing import Any

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.parametros import param_int
from apps.core.cache import obter_ou_marcar_para_atualizar
from apps.serap import fallback
from apps.serap import tasks
from apps.serap.api.serializers import MetricasSerapSerializer
from apps.serap.constants import chave_cache_metricas


class MetricasSerapView(APIView):
    """Métricas do SERAp, orquestradas a partir do backend (cache-aside).

    Lê o contrato já consolidado no cache, por ano e bimestre. Quando o
    cache está frio, dispara ``tasks.atualizar_metricas`` em background e
    devolve imediatamente o contrato de fallback.
    """

    serializer_class = MetricasSerapSerializer

    @extend_schema(
        tags=["serap"],
        summary="Métricas do SERAp",
        operation_id="serap_metricas",
        parameters=[
            OpenApiParameter("ano", int, required=True, description="Ano."),
            OpenApiParameter(
                "bimestre", int, required=True, description="Bimestre."
            ),
        ],
        responses=MetricasSerapSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o contrato de métricas do SERAp para o período."""
        ano = param_int(request, "ano")
        bimestre = param_int(request, "bimestre")

        payload = obter_ou_marcar_para_atualizar(
            chave_cache_metricas(ano, bimestre),
            tasks.atualizar_metricas,
            (ano, bimestre),
            ttl_lock=settings.SERAP_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = fallback.metricas_indisponivel(ano, bimestre)

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
