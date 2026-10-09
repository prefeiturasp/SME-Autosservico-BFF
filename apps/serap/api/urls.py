"""Rotas do app serap."""

from django.urls import path

from apps.serap.api.views import MetricasSerapView

app_name = "serap"
urlpatterns = [
    path("serap/metricas/", MetricasSerapView.as_view(), name="metricas"),
]
