"""URL configuration raiz do projeto SME Autosservico BFF."""

from django.urls import include
from django.urls import path
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView

_API_V1 = "api/v1/"

urlpatterns = [
    path(_API_V1, include("apps.core.api.urls", namespace="core")),
    path(_API_V1, include("apps.zabbix.api.urls", namespace="zabbix")),
    path(_API_V1, include("apps.azure.api.urls", namespace="azure")),
    path(_API_V1, include("config.api_router")),
    path(f"{_API_V1}schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        f"{_API_V1}docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]
