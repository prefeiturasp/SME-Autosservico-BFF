"""Rotas do app gipe."""

from django.urls import path

from apps.gipe.api.views import MetricasGipeView

app_name = "gipe"
urlpatterns = [
    path(
        "gipe/metricas/",
        MetricasGipeView.as_view(),
        name="metricas",
    ),
]
