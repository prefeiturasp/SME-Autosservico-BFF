"""Rotas do app bensfisicos."""

from django.urls import path

from apps.bensfisicos.api.views import MetricasBensFisicosView

app_name = "bensfisicos"
urlpatterns = [
    path(
        "bens-fisicos/metricas/",
        MetricasBensFisicosView.as_view(),
        name="metricas",
    ),
]
