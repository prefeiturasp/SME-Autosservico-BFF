"""Views do app bensfisicos.

Cache-aside: a view só lê o cache e, se estiver frio, dispara
``tasks.atualizar_metricas`` e devolve o fallback na hora. Nunca importa
``apps.bensfisicos.client``.
"""

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bensfisicos import fallback
from apps.bensfisicos import tasks
from apps.bensfisicos.api.serializers import MetricasBensFisicosSerializer
from apps.bensfisicos.constants import CHAVE_CACHE_METRICAS
from apps.core.cache import obter_ou_marcar_para_atualizar


class MetricasBensFisicosView(APIView):
    """Métricas do Bens Físicos, orquestradas a partir do backend."""

    serializer_class = MetricasBensFisicosSerializer

    @extend_schema(
        tags=["bens-fisicos"],
        summary="Métricas do Bens Físicos",
        operation_id="bens_fisicos_metricas",
        responses=MetricasBensFisicosSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o contrato de métricas do Bens Físicos."""
        payload = obter_ou_marcar_para_atualizar(
            CHAVE_CACHE_METRICAS,
            tasks.atualizar_metricas,
            (),
            ttl_lock=settings.BENS_FISICOS_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = fallback.metricas_indisponivel()

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
