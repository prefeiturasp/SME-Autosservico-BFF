.. _core:

Core
======================================================================

O app ``core`` concentra autenticação (chave de API), o endpoint de
health check e utilidades compartilhadas entre os demais domínios.

Arquitetura (nível C3)
----------------------------------------------------------------------

Este BFF é estritamente *stateless* (sem banco de dados relacional nem
migrations locais) e segue três camadas:

1. **Camada de Request (síncrona)**: recebe a requisição HTTP do
   frontend, valida a API Key e consulta o estado já cacheado no
   ``BFF_BROKER`` — nunca faz chamadas de I/O externas em tempo de
   requisição.
2. **Broker e Cache (KeyDB)**: o ``BFF_BROKER`` tem papel duplo — cache
   dos payloads agregados para a UI, e message broker das tasks do
   Celery (ver ``config/celery.py``).
3. **Background (Celery Workers)**: consumidores assíncronos que
   executarão as integrações reais (Zabbix, Jenkins, Azure DevOps,
   Grafana) quando implementadas.

Health Check
----------------------------------------------------------------------

Endpoint utilizado por probes de liveness/orquestradores para verificar
se o processo da aplicação está no ar.

.. automodule:: apps.core.api.views
   :members:
   :noindex:

.. automodule:: apps.core.api.serializers
   :members:
   :noindex:

Autenticação
----------------------------------------------------------------------

Esquema de autenticação por chave de API (header HTTP), padrão SME para
microsserviços. Como este serviço não possui banco de dados/usuários, o
schema OpenAPI e o Swagger UI também são protegidos pela mesma API Key,
em vez de login de superusuário.

.. automodule:: apps.core.authentication
   :members:
   :noindex:

Conectores genéricos de métricas
----------------------------------------------------------------------

Infraestrutura reaproveitável por qualquer domínio futuro de
métricas/indicadores, adiantada a partir de duas provas de conceito
(POC) que investigaram como trazer indicadores de sistemas legados da
SME (piloto: SGP) para o Autosserviço:

- **POC 1** (``poc-sgp-elasticsearch``): métricas já agregadas no ELK
  Stack (Elasticsearch/Kibana) da SME — indicadores diários de acesso
  já validados via query (total de ontem, média de 30 dias, evolução
  histórica). Ver :mod:`apps.core.client_kibana`.
- **POC 2** (``POC-Metricas-SGP``, Spassu): leitura somente-leitura,
  via SQL puro, do PostgreSQL de cada sistema de origem — cobre
  indicadores que não existem no Elastic (ex.: usuários com acesso
  ativo, usuários de unidades educacionais, dados que vivem só no
  banco relacional do sistema). Ver :mod:`apps.core.postgres_leitura`.

**Nenhum dos dois ainda tem domínio de negócio consumindo-os** — só o
cliente/utilitário de baixo nível está disponível. Quando o primeiro
indicador real for implementado, a regra arquitetural de sempre se
aplica: o I/O real (chamada ao Kibana, leitura no Postgres externo) só
pode acontecer dentro de uma Celery task, nunca na view síncrona — a
view só lê o cache (mesmo padrão de ``apps/zabbix`` e ``apps/azure``).

.. automodule:: apps.core.client_kibana
   :members:
   :noindex:

.. automodule:: apps.core.postgres_leitura
   :members:
   :noindex:

Roadmap
----------------------------------------------------------------------

Este BFF é a camada de orquestração e roteamento entre o frontend e as
demais fontes de dados do autosserviço. Além do
``SME-Autosservico-Backend``, Zabbix e Azure DevOps (já integrados) e
da infraestrutura de Celery/KeyDB (já disponível), os próximos passos
previstos são:

- Integração do **SME Sidecar SDK** (circuit breaker/retry + tracing),
  pré-requisito das integrações abaixo.
- Domínio de métricas/indicadores (SGP piloto) usando os conectores
  genéricos acima — nome do app e escopo do primeiro indicador ainda
  em definição.
- Demais sistemas candidatos ao mesmo padrão de conector, conforme a
  POC 2: SIGPAE, CoreSSO, PTRF.

Cada um deve ganhar seu próprio app de domínio (``apps/<dominio>``) e a
respectiva página em ``docs/dominios/<dominio>/index.rst`` quando for
implementado.
