"""Endpoint de health check usado por probes de liveness e load balancers."""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.serializers import HealthCheckSerializer


class HealthCheckView(APIView):
    """Reporta se o processo da aplicação está no ar e respondendo.

    Não realiza, por enquanto, nenhuma checagem de dependência externa
    (backend, Azure DevOps, Zabbix, Grafana), já que essas integrações
    ainda não foram implementadas. Quando forem, estender ``get`` para
    reportar status degradado em caso de falha de alguma dependência.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = HealthCheckSerializer

    @extend_schema(
        tags=["core"],
        summary="Health check",
        operation_id="core_health_check",
        responses=HealthCheckSerializer,
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retorna o payload de liveness do serviço.

        Returns:
            Response: corpo JSON ``{"status": "ok"}`` com HTTP 200.
        """
        serializer = self.serializer_class(data={"status": "ok"})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
