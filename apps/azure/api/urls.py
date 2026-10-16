"""Rotas do app azure."""

from django.urls import path

from apps.azure.api.views import BacklogDiagnosticsView
from apps.azure.api.views import BacklogView
from apps.azure.api.views import ProjectsView

app_name = "azure"
urlpatterns = [
    path("azure/backlog/", BacklogView.as_view(), name="backlog"),
    path(
        "azure/backlog/diagnostics/",
        BacklogDiagnosticsView.as_view(),
        name="backlog-diagnostics",
    ),
    path("azure/projects/", ProjectsView.as_view(), name="projects"),
]
