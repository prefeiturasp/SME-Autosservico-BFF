"""Dados estáticos usados na integração com o Azure DevOps.

Este módulo não faz nenhuma chamada de rede — só declara os parâmetros
fixos usados pelo serviço (``apps/azure/services/``) para montar as
consultas WIQL e classificar os work items retornados.
"""

import re

# Endpoint público do Azure DevOps e versão da REST API usada em todas as
# chamadas. Só variam num Azure DevOps Server on-premises, cenário que
# este BFF não atende — por isso são constantes, e não variáveis de
# ambiente: o ``.env`` fica só com o que muda por ambiente (o PAT e a
# organização).
URL_BASE_API = "https://dev.azure.com"
VERSAO_API = "7.0"

TIMEOUT_HTTP_SEGUNDOS = 30

# Teto de ids devolvidos pela consulta WIQL.
LIMITE_IDS_WIQL = 20_000

# TTLs do cache de estado da UI (BFF_BROKER). A lista de projetos muda
# raramente; o diagnóstico acompanha o TTL do backlog, já que é derivado
# da mesma carga.
TTL_CACHE_BACKLOG_SEGUNDOS = 300
TTL_CACHE_PROJETOS_SEGUNDOS = 1800
TTL_CACHE_DIAGNOSTICO_SEGUNDOS = 300

# Janela do lock que impede disparar a mesma task duas vezes.
TTL_LOCK_SEGUNDOS = 120

# O backlog é paginado em lotes de 200 ids, então uma carga grande passa
# bem de CELERY_TASK_TIME_LIMIT (30s, dimensionado para o Zabbix). As
# tasks deste app usam este limite próprio, ver apps/azure/tasks.py.
LIMITE_TEMPO_TASK_SEGUNDOS = 600

RECURSO_WIQL = "_apis/wit/wiql"
RECURSO_WORK_ITEMS = "_apis/wit/workitems"
RECURSO_PROJETOS = "_apis/projects"

# Header em que o Azure devolve o token da próxima página de projetos.
CABECALHO_TOKEN_CONTINUACAO = "x-ms-continuationtoken"  # noqa: S105

# Paginação de projetos (mesmos limites validados pela Azure API).
PROJETOS_TOP_PADRAO = 100
PROJETOS_TOP_MINIMO = 1
PROJETOS_TOP_MAXIMO = 500

# Diagnóstico: recorte do título e tamanho da amostra de work items.
DIAGNOSTICO_TAMANHO_TITULO = 80
DIAGNOSTICO_TAMANHO_AMOSTRA = 20
DIAGNOSTICO_TIPO_DESCONHECIDO = "Unknown"

# O Azure só devolve os detalhes de um lote de ids por requisição.
TAMANHO_LOTE_WORK_ITEMS = 200

# Relação usada pelo Azure para apontar o item pai na hierarquia.
RELACAO_PAI = "System.LinkTypes.Hierarchy-Reverse"

# Tipos considerados "pais" na resposta; todo o resto vira "filho".
TIPOS_WORK_ITEM_PAI = frozenset(
    {"Epic", "Feature", "User Story", "Product Backlog Item"}
)

# Agrupamento de estados usado nas métricas de bugs.
ESTADOS_ABERTOS = frozenset({"New", "Approved"})
ESTADOS_EM_ANDAMENTO = frozenset({"Active", "Testing", "Blocked"})
ESTADOS_RESOLVIDOS = frozenset({"Resolved", "Done"})

CAMPO_TITULO = "System.Title"
CAMPO_ESTADO = "System.State"
CAMPO_TIPO = "System.WorkItemType"
CAMPO_TAGS = "System.Tags"
CAMPO_CRIADO_POR = "System.CreatedBy"
CAMPO_ATRIBUIDO_A = "System.AssignedTo"
CAMPO_AREA = "System.AreaPath"
CAMPO_PROJETO = "System.TeamProject"
CAMPO_ITERACAO = "System.IterationPath"
CAMPO_TRABALHO_CONCLUIDO = "Microsoft.VSTS.Scheduling.CompletedWork"
CAMPO_ESTIMATIVA = "Microsoft.VSTS.Scheduling.OriginalEstimate"
CAMPO_DATA_INICIO = "Microsoft.VSTS.Scheduling.StartDate"
CAMPO_DATA_FIM = "Microsoft.VSTS.Scheduling.FinishDate"
CAMPO_DATA_CRIACAO = "System.CreatedDate"
CAMPO_DATA_ALTERACAO = "System.ChangedDate"
CAMPO_DATA_FECHAMENTO = "Microsoft.VSTS.Common.ClosedDate"
CAMPO_DATA_RESOLUCAO = "Microsoft.VSTS.Common.ResolvedDate"

# Filtros aceitos pelo endpoint, na ordem em que viram cláusulas WIQL.
# Cada chave é o nome do query param; o valor, o campo do Azure.
FILTROS_IN: dict[str, str] = {
    "work_item_types": CAMPO_TIPO,
    "states": CAMPO_ESTADO,
}
FILTROS_UNDER: dict[str, str] = {
    "area_paths": CAMPO_AREA,
    "iteration_paths": CAMPO_ITERACAO,
}
FILTROS_IN_FINAL: dict[str, str] = {
    "assigned_to": CAMPO_ATRIBUIDO_A,
}
FILTRO_CONTAINS = "tags"

# Chaves de filtro que chegam como lista (valores separados por vírgula).
CHAVES_FILTRO_LISTA = (
    *FILTROS_IN,
    *FILTROS_UNDER,
    *FILTROS_IN_FINAL,
)

FORMATO_DATA_ENTRADA = "%Y-%m-%d"
FORMATO_DATA_SAIDA = "%d/%m/%Y"

# Caracteres de controle nunca aparecem em valor legítimo de filtro e
# são removidos antes de compor o literal WIQL (ver services/backlog.py).
REGEX_CARACTERES_CONTROLE = re.compile(r"[\x00-\x1f\x7f]")
