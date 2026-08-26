"""Rotas do app sigpae."""

from django.urls import path

from apps.sigpae.api.views import MetricasSigpaeView

app_name = "sigpae"
urlpatterns = [
    path("sigpae/metricas/", MetricasSigpaeView.as_view(), name="metricas"),
]
