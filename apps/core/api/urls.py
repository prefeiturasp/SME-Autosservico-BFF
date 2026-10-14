"""Rotas do app core."""

from django.urls import path

from apps.core.api.views import HealthCheckView

app_name = "core"
urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
]
