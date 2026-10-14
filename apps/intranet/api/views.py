"""Views do app intranet."""

import re
from typing import Any

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import obter_ou_marcar_para_atualizar
from apps.intranet import fallback
from apps.intranet import tasks
from apps.intranet.api.serializers import MetricasIntranetSerializer
from apps.intranet.constants import PERIODO_GERAL
from apps.intranet.constants import PERIODOS
from apps.intranet.constants import chave_cache_metricas

_FORMATO_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _param_periodo(request: Request) -> str:
    """Lê ``periodo`` da query string (padrão ``geral``).

    Raises:
        ValidationError: Período fora de ``PERIODOS``.
    """
    periodo = request.query_params.get("periodo") or PERIODO_GERAL
    if periodo not in PERIODOS:
        opcoes = ", ".join(PERIODOS)
        raise ValidationError({"periodo": [f"Use um de: {opcoes}."]})
    return periodo


def _param_mes(request: Request) -> str | None:
    """Lê ``mes`` (``AAAA-MM``) da query string, se informado.

    Raises:
        ValidationError: Formato inválido.
    """
    mes = request.query_params.get("mes") or None
    if mes is not None and not _FORMATO_MES.match(mes):
        raise ValidationError({"mes": ["Use o formato AAAA-MM."]})
    return mes


class MetricasIntranetView(APIView):
    """Métricas do Intranet lidas do cache.

    Com o cache frio, dispara a atualização em background e responde com
    o fallback.
    """

    serializer_class = MetricasIntranetSerializer

    @extend_schema(
        tags=["intranet"],
        summary="Métricas do Intranet",
        operation_id="intranet_metricas",
        parameters=[
            OpenApiParameter(
                "periodo",
                str,
                required=False,
                enum=list(PERIODOS),
                description=(
                    "Recorte dos cards por tipo/ganhador/DRE (janela "
                    "móvel). Padrão: geral (sem filtro de data)."
                ),
            ),
            OpenApiParameter(
                "mes",
                str,
                required=False,
                description=(
                    "Mês (AAAA-MM) do card por DRE de Ordem de Inscrição. "
                    "Ausente: sem filtro de data."
                ),
            ),
        ],
        responses=MetricasIntranetSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna as métricas do Intranet."""
        periodo = _param_periodo(request)
        mes = _param_mes(request)

        payload = obter_ou_marcar_para_atualizar(
            chave_cache_metricas(periodo, mes),
            tasks.atualizar_metricas,
            (periodo, mes),
            ttl_lock=settings.INTRANET_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = fallback.metricas_indisponivel(periodo, mes)

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
