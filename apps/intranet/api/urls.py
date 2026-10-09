"""Rotas do app intranet."""

from django.urls import path

from apps.intranet.api.views import MetricasIntranetView

app_name = "intranet"
urlpatterns = [
    path(
        "intranet/metricas/",
        MetricasIntranetView.as_view(),
        name="metricas",
    ),
]
