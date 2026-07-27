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

Roadmap
----------------------------------------------------------------------

Este BFF é a camada de orquestração e roteamento entre o frontend e as
demais fontes de dados do autosserviço. Além do
``SME-Autosservico-Backend`` (já integrado) e da infraestrutura de
Celery/KeyDB (já disponível, sem tasks reais ainda), os próximos passos
previstos são:

- Integração do **SME Sidecar SDK** (circuit breaker/retry + tracing),
  pré-requisito das integrações abaixo.
- Azure DevOps (status de bugs/pipelines).
- Zabbix (saúde do sistema).
- Grafana (observabilidade/telemetria).

Cada um deve ganhar seu próprio app de domínio (``apps/<dominio>``) e a
respectiva página em ``docs/dominios/<dominio>/index.rst`` quando for
implementado.
