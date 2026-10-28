"""Views do app gipe.

Cache-aside por ano letivo: a view valida a query string, lê o cache e, se
estiver frio, dispara ``tasks.atualizar_metricas`` e devolve o fallback na
hora. Nunca importa ``apps.gipe.client``.
"""

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import obter_ou_marcar_para_atualizar
from apps.gipe import fallback
from apps.gipe import tasks
from apps.gipe.api.serializers import GipeFiltrosQuerySerializer
from apps.gipe.api.serializers import MetricasGipeSerializer
from apps.gipe.constants import ano_letivo_corrente
from apps.gipe.constants import chave_cache_metricas


class MetricasGipeView(APIView):
    """Métricas do GIPE, orquestradas a partir do backend.

    Lê o contrato já consolidado no cache, pelo ano letivo (o corrente,
    quando a query não traz). Quando o cache está frio, dispara
    ``tasks.atualizar_metricas`` em background e devolve imediatamente o
    contrato de fallback.
    """

    serializer_class = MetricasGipeSerializer

    @extend_schema(
        tags=["gipe"],
        summary="Métricas do GIPE",
        operation_id="gipe_metricas",
        parameters=[GipeFiltrosQuerySerializer],
        responses=MetricasGipeSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o contrato de métricas do GIPE para o ano letivo."""
        params = GipeFiltrosQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        ano_letivo = params.validated_data.get("ano_letivo")
        if ano_letivo is None:
            ano_letivo = ano_letivo_corrente()

        payload = obter_ou_marcar_para_atualizar(
            chave_cache_metricas(ano_letivo),
            tasks.atualizar_metricas,
            (ano_letivo,),
            ttl_lock=settings.GIPE_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = fallback.metricas_indisponivel(ano_letivo)

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
