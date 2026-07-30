"""Serializers da API do app azure.

Os campos seguem exatamente o contrato já consumido pelo frontend, em
``snake_case``. Campos opcionais usam ``allow_null=True`` — e não a
omissão adotada no app zabbix — porque o contrato existente sempre
emite a chave, com ``null`` quando não há valor.
"""

from rest_framework import serializers


class WorkItemSerializer(serializers.Serializer):
    """Work item do backlog, no formato consumido pelo frontend."""

    id = serializers.IntegerField()
    title = serializers.CharField(allow_blank=True)
    state = serializers.CharField(allow_null=True, allow_blank=True)
    work_item_type = serializers.CharField(allow_null=True, allow_blank=True)
    tags = serializers.CharField(allow_null=True, allow_blank=True)
    created_by = serializers.CharField(allow_null=True, allow_blank=True)
    assigned_to = serializers.CharField(allow_null=True, allow_blank=True)
    area_path = serializers.CharField(allow_null=True, allow_blank=True)
    team_project = serializers.CharField(allow_null=True, allow_blank=True)
    iteration_path = serializers.CharField(allow_null=True, allow_blank=True)
    completed_work = serializers.FloatField(allow_null=True)
    original_estimate = serializers.FloatField(allow_null=True)
    start_date = serializers.CharField(allow_null=True, allow_blank=True)
    finish_date = serializers.CharField(allow_null=True, allow_blank=True)
    created_date = serializers.CharField(allow_null=True, allow_blank=True)
    changed_date = serializers.CharField(allow_null=True, allow_blank=True)
    closed_date = serializers.CharField(allow_null=True, allow_blank=True)
    parent_id = serializers.IntegerField(allow_null=True)
    parent_link = serializers.CharField(allow_null=True, allow_blank=True)


class BugMetricsSerializer(serializers.Serializer):
    """Métricas agregadas da seção de bugs."""

    total_cycle = serializers.IntegerField()
    open = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    resolved = serializers.IntegerField()
    average_resolution = serializers.CharField(
        allow_null=True, allow_blank=True
    )


class BacklogSerializer(serializers.Serializer):
    """Backlog completo de um projeto do Azure DevOps."""

    total_items = serializers.IntegerField()
    parents = WorkItemSerializer(many=True)
    children = WorkItemSerializer(many=True)
    bug_metrics = BugMetricsSerializer()
    metadata = serializers.DictField()


def _lista_opcional() -> serializers.ListField:
    """Monta um campo de lista de textos opcional.

    Returns:
        Campo pronto para um filtro de lista do corpo do ``POST``.
    """
    return serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        allow_null=True,
    )


class WorkItemFiltersSerializer(serializers.Serializer):
    """Filtros adicionais aceitos no corpo do ``POST /backlog/``."""

    work_item_types = _lista_opcional()
    states = _lista_opcional()
    area_paths = _lista_opcional()
    iteration_paths = _lista_opcional()
    assigned_to = _lista_opcional()
    tags = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class BacklogRequestSerializer(serializers.Serializer):
    """Corpo aceito pelo ``POST /backlog/``.

    Mesmo contrato de entrada do serviço que este app substitui. O campo
    ``pat`` é aceito por compatibilidade, mas **ignorado**: o token vem
    sempre de ``AZURE_DEVOPS_PAT``, nunca da requisição.
    """

    project_name = serializers.CharField()
    organization = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    pat = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    start_date = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    end_date = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    year = serializers.IntegerField(required=False, allow_null=True)
    month = serializers.IntegerField(required=False, allow_null=True)
    filters = WorkItemFiltersSerializer(required=False, allow_null=True)


class ProjectSerializer(serializers.Serializer):
    """Projeto do Azure DevOps."""

    id = serializers.CharField(allow_blank=True)
    name = serializers.CharField(allow_blank=True)
    description = serializers.CharField(allow_null=True, allow_blank=True)
    url = serializers.CharField(allow_null=True, allow_blank=True)
    state = serializers.CharField(allow_null=True, allow_blank=True)
    revision = serializers.IntegerField(allow_null=True)
    visibility = serializers.CharField(allow_null=True, allow_blank=True)
    last_update_time = serializers.CharField(allow_null=True, allow_blank=True)


class ProjectsListSerializer(serializers.Serializer):
    """Listagem paginada de projetos de uma organização."""

    count = serializers.IntegerField()
    total_count = serializers.IntegerField(allow_null=True)
    projects = ProjectSerializer(many=True)
    continuation_token = serializers.CharField(
        allow_null=True, allow_blank=True
    )
    has_more = serializers.BooleanField()


class DiagnosticSampleItemSerializer(serializers.Serializer):
    """Amostra compacta de um work item no diagnóstico."""

    id = serializers.IntegerField()
    title = serializers.CharField(allow_blank=True)
    type = serializers.CharField(allow_null=True, allow_blank=True)
    state = serializers.CharField(allow_null=True, allow_blank=True)


class BacklogDiagnosticsSerializer(serializers.Serializer):
    """Contagem de work items por tipo, com amostra."""

    project_name = serializers.CharField()
    total_items = serializers.IntegerField()
    work_item_type_counts = serializers.DictField(
        child=serializers.IntegerField()
    )
    sample_items = DiagnosticSampleItemSerializer(many=True)
