"""Views do app sigescola.

Cache-aside por combinação de filtros: a view valida a query string, lê o
cache e, se estiver frio, dispara ``tasks.atualizar_metricas`` e devolve o
fallback na hora. Nunca importa ``apps.sigescola.client``.
"""

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import obter_ou_marcar_para_atualizar
from apps.sigescola import fallback
from apps.sigescola import tasks
from apps.sigescola.api.serializers import MetricasSigEscolaSerializer
from apps.sigescola.api.serializers import SigEscolaFiltrosQuerySerializer
from apps.sigescola.constants import chave_cache_metricas


class MetricasSigEscolaView(APIView):
    """Métricas do SIG-Escola, orquestradas a partir do backend.

    Lê o contrato já consolidado no cache, pela combinação de filtros.
    Quando o cache está frio, dispara ``tasks.atualizar_metricas`` em
    background e devolve imediatamente o contrato de fallback.
    """

    serializer_class = MetricasSigEscolaSerializer

    @extend_schema(
        tags=["sigescola"],
        summary="Métricas do SIG-Escola",
        operation_id="sigescola_metricas",
        parameters=[SigEscolaFiltrosQuerySerializer],
        responses=MetricasSigEscolaSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o contrato de métricas do SIG-Escola para os filtros."""
        params = SigEscolaFiltrosQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        filtros = {
            nome: str(valor) for nome, valor in params.validated_data.items()
        }

        payload = obter_ou_marcar_para_atualizar(
            chave_cache_metricas(filtros),
            tasks.atualizar_metricas,
            (filtros,),
            ttl_lock=settings.SIGESCOLA_LOCK_TTL_SECONDS,
        )
        if payload is None:
            payload = fallback.metricas_indisponivel(filtros)

        serializer = self.serializer_class(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
