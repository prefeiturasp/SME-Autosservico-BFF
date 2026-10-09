"""Rotas do app sigescola."""

from django.urls import path

from apps.sigescola.api.views import MetricasSigEscolaView

app_name = "sigescola"
urlpatterns = [
    path(
        "sigescola/metricas/",
        MetricasSigEscolaView.as_view(),
        name="metricas",
    ),
]
