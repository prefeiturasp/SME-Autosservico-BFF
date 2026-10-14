.. _azure:

Azure DevOps
======================================================================

Integração com a REST API do Azure DevOps para o backlog de work items
e as métricas de bugs consumidas pelo dashboard do autosserviço. O BFF
fala diretamente com ``dev.azure.com``, sem nenhum serviço
intermediário, e devolve o mesmo contrato de resposta que o frontend já
consome.

Endpoints
----------------------------------------------------------------------

* ``GET|POST /api/v1/azure/backlog/`` — backlog do projeto. O ``GET``
  recebe os filtros como query params separados por vírgula; o ``POST``,
  como listas no corpo. Filtros equivalentes resolvem para a mesma
  chave de cache nas duas formas.
* ``GET /api/v1/azure/backlog/diagnostics/`` — contagem de work items
  por tipo, com amostra dos 20 primeiros.
* ``GET /api/v1/azure/projects/`` — projetos da organização, paginados.

O campo ``pat`` é aceito no corpo do ``POST`` por compatibilidade com o
contrato antigo, mas **ignorado**: o token vem sempre de
``AZURE_DEVOPS_PAT``, nunca da requisição.

Arquitetura
----------------------------------------------------------------------

A camada de request síncrona (``api/views.py``) nunca chama o Azure
diretamente — só lê o cache do ``BFF_BROKER`` (KeyDB):

1. Em cache hit, devolve o backlog já processado na hora.
2. Em cache miss, dispara ``tasks.atualizar_backlog`` em background —
   protegida por um lock atômico no próprio cache, para não duplicar
   disparos — e devolve imediatamente um backlog vazio. Esse fallback é
   exatamente o mesmo payload que o Azure produz quando a consulta não
   encontra work items, então a interface não quebra (diretriz 2 do
   nível C3).
3. Não há Celery Beat neste domínio: o backlog recebe filtros
   arbitrários do frontend (projeto, período, tipos, estados, sprint),
   sem catálogo fixo no BFF — por isso o padrão é cache-aside sob
   demanda, como nos presets de status do Zabbix, e não a atualização
   periódica usada no status de banco de dados.

A chave de cache cobre organização, projeto, período e todos os
filtros, serializados com as chaves ordenadas: a mesma combinação
sempre resolve para a mesma chave, independentemente da ordem dos query
params.

Fluxo da consulta
----------------------------------------------------------------------

Uma carga de backlog custa duas etapas no Azure:

1. ``POST _apis/wit/wiql`` devolve apenas os ids que casam com os
   filtros.
2. ``GET _apis/wit/workitems`` busca os detalhes em lotes de 200 ids,
   com ``$expand=relations`` para resolver o item pai.

Por isso as tasks deste app usam ``LIMITE_TEMPO_TASK_SEGUNDOS``
(``apps/azure/constants.py``) em vez do ``CELERY_TASK_TIME_LIMIT``
global: uma carga grande passa com folga dos 30 segundos dimensionados
para o Zabbix.

Configuração
----------------------------------------------------------------------

O ``.env`` traz apenas o que muda por ambiente: ``AZURE_DEVOPS_PAT`` e
``AZURE_DEVOPS_ORGANIZATION``. Endpoint, versão da API, timeout, TTLs de
cache e limites de paginação são constantes em
``apps/azure/constants.py`` — mudá-los é uma decisão de código, com
revisão, e não de operação.

Segurança da consulta WIQL
----------------------------------------------------------------------

A API do Azure não oferece bind de parâmetros, então a WIQL é montada
por interpolação. Todo valor de origem externa — nome do projeto,
datas e filtros — passa antes por ``_literal_wiql``, que duplica aspas
simples e remove caracteres de controle, impedindo que um filtro
encerre o literal e injete cláusulas na consulta. Os nomes de campo são
constantes do módulo, nunca entrada do usuário.

Backlog
----------------------------------------------------------------------

.. automodule:: apps.azure.services.backlog
   :members:
   :noindex:

Formatação de datas e durações
----------------------------------------------------------------------

.. automodule:: apps.azure.services.formatacao
   :members:
   :noindex:

Cliente Azure DevOps
----------------------------------------------------------------------

.. automodule:: apps.azure.client
   :members:
   :noindex:

Projetos
----------------------------------------------------------------------

.. automodule:: apps.azure.services.projetos
   :members:
   :noindex:

Diagnóstico
----------------------------------------------------------------------

.. automodule:: apps.azure.services.diagnostico
   :members:
   :noindex:

Cache e tasks
----------------------------------------------------------------------

.. automodule:: apps.azure.cache
   :members:
   :noindex:

.. automodule:: apps.azure.tasks
   :members:
   :noindex:
