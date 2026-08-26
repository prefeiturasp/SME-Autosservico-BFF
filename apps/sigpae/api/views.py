"""Views do app sigpae.

A view não importa ``apps.sigpae.client`` — só lê o cache (via
``apps.core.cache``) e dispara a task de atualização em background quando
o cache está frio, devolvendo imediatamente o contrato de fallback.
"""

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import obter_ou_marcar_para_atualizar
from apps.sigpae import fallback
from apps.sigpae import tasks
from apps.sigpae.api.serializers import MetricasSigpaeSerializer
from apps.sigpae.constants import CHAVE_CACHE_METRICAS


class MetricasSigpaeView(APIView):
    """Métricas do SIGPAE, orquestradas a partir do backend (cache-aside).

    Lê o contrato já consolidado no cache. Quando o cache está frio,
    dispara ``tasks.atualizar_metricas`` em background e devolve
    imediatamente o contrato de fallback (indicadores nulos).
    """

    serializer_class = MetricasSigpaeSerializer

    @extend_schema(
        tags=["sigpae"],
        summary="Métricas do SIGPAE",
        operation_id="sigpae_metricas",
        responses=MetricasSigpaeSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o contrato de métricas do SIGPAE."""
        payload = obter_ou_marcar_para_atualizar(
            CHAVE_CACHE_METRICAS,
            tasks.atualizar_metricas,
            (),
            ttl_lock=settings.SIGPAE_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = fallback.metricas_indisponivel()

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
