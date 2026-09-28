"""Rotas do app sgp."""

from django.urls import path

from apps.sgp.api.views import MetricasSgpView

app_name = "sgp"
urlpatterns = [
    path("sgp/metricas/", MetricasSgpView.as_view(), name="metricas"),
]
