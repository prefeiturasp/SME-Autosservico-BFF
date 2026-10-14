.. _zabbix:

Zabbix
======================================================================

Integração com o Zabbix para status de disponibilidade, status de
banco de dados e resumo de build do Jenkins (que também é lido via
``item.get`` do Zabbix — outro sistema já coleta os dados do Jenkins e
grava um resumo no item). Porta a integração que hoje vive no
``SME-Autosservico-Frontend``, mantendo o mesmo contrato de rotas e
formato de resposta.

Arquitetura
----------------------------------------------------------------------

A camada de request síncrona (``api/views.py``) nunca chama o Zabbix
diretamente — só lê o cache do ``BFF_BROKER`` (KeyDB):

1. Em cache hit, devolve o valor já processado na hora.
2. Em cache miss, dispara a Celery task correspondente
   (``tasks.py``) em background — protegida por um lock atômico
   no próprio cache, para não duplicar disparos — e devolve
   imediatamente um fallback seguro, no mesmo formato que o frontend
   já consome hoje.
3. O status de banco de dados também é atualizado periodicamente por
   uma Celery Beat (``zabbix.atualizar_status_bancos``), já que tem um
   conjunto finito e conhecido de sistemas
   (``constants.CONFIGURACAO_BANCOS_POR_SISTEMA``). Os presets de
   status e o resumo do Jenkins recebem parâmetros arbitrários do
   frontend (sem catálogo fixo no BFF), por isso usam o padrão
   cache-aside sob demanda.

Status de disponibilidade
----------------------------------------------------------------------

Presets ``producao`` (disponibilidade do ambiente) e ``filas`` (saúde
de filas/RabbitMQ), ambos baseados em ``trigger.get``.

.. automodule:: apps.zabbix.services.status
   :members:
   :noindex:

Status de banco de dados
----------------------------------------------------------------------

.. automodule:: apps.zabbix.services.database
   :members:
   :noindex:

Resumo de build do Jenkins
----------------------------------------------------------------------

.. automodule:: apps.zabbix.services.jenkins
   :members:
   :noindex:

Cliente Zabbix
----------------------------------------------------------------------

.. automodule:: apps.zabbix.client
   :members:
   :noindex:
