"""Rotas do app zabbix."""

from django.urls import path

from apps.zabbix.api.views import DatabaseStatusView
from apps.zabbix.api.views import JenkinsJobSummaryView
from apps.zabbix.api.views import SistemasDisponibilidadeView
from apps.zabbix.api.views import StatusPresetView

app_name = "zabbix"
urlpatterns = [
    path(
        "zabbix/status/<str:preset>/",
        StatusPresetView.as_view(),
        name="status-preset",
    ),
    path(
        "zabbix/disponibilidade/sistemas/",
        SistemasDisponibilidadeView.as_view(),
        name="disponibilidade-sistemas",
    ),
    path("zabbix/database/", DatabaseStatusView.as_view(), name="database"),
    path(
        "zabbix/jenkins/job/",
        JenkinsJobSummaryView.as_view(),
        name="jenkins-job",
    ),
]
