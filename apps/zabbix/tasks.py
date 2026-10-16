"""Celery tasks da integração com o Zabbix.

Nenhuma task usa retry próprio (``bind=True``/``self.retry``) — o
retry de transporte já é feito inteiramente dentro de
``apps.zabbix.client``. Se uma task falhar (ex.: Zabbix indisponível
além do orçamento de retry do client), ela só falha e loga; a chave de
cache correspondente continua ausente/expirada, e a próxima requisição
(ou o próximo tick do Beat, no caso do banco de dados) tenta de novo
naturalmente.
"""

from typing import Literal

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from apps.zabbix import cache as zabbix_cache
from apps.zabbix.constants import CONFIGURACAO_BANCOS_POR_SISTEMA
from apps.zabbix.services import database as servico_database
from apps.zabbix.services import jenkins as servico_jenkins
from apps.zabbix.services import status as servico_status


@shared_task(name="zabbix.atualizar_status")
def atualizar_status(preset: str, host: str, project: str) -> None:
    """Consulta o Zabbix e atualiza o cache de status de disponibilidade.

    Args:
        preset: Nome do preset (``producao`` ou ``filas``).
        host: Host do Zabbix consultado.
        project: Projeto/descrição do trigger consultado.
    """
    status = servico_status.obter_status(preset, project, host)
    chave = zabbix_cache.chave_status(preset, host, project)
    cache.set(chave, status, timeout=settings.ZABBIX_CACHE_TTL_STATUS_SECONDS)


@shared_task(name="zabbix.atualizar_jenkins_job")
def atualizar_jenkins_job(
    project: str, ambiente: Literal["prod", "homolog"]
) -> None:
    """Consulta o Zabbix e atualiza o cache do resumo de build do Jenkins.

    Args:
        project: Nome/caminho do job.
        ambiente: ``"prod"`` ou ``"homolog"``.
    """
    resumo = servico_jenkins.obter_resumo(project, ambiente)
    chave = zabbix_cache.chave_jenkins(project, ambiente)
    cache.set(chave, resumo, timeout=settings.ZABBIX_CACHE_TTL_JENKINS_SECONDS)


@shared_task(name="zabbix.atualizar_status_banco_sistema")
def atualizar_status_banco_sistema(sistema: str) -> None:
    """Consulta o Zabbix e atualiza o cache de status de banco de um sistema.

    Args:
        sistema: Nome de exibição do sistema.
    """
    status = servico_database.obter_status_banco(sistema)
    chave = zabbix_cache.chave_database(sistema)
    cache.set(
        chave, status, timeout=settings.ZABBIX_CACHE_TTL_DATABASE_SECONDS
    )


@shared_task(name="zabbix.atualizar_status_bancos")
def atualizar_status_bancos() -> None:
    """Dispara a atualização de cache de todo sistema com banco configurado.

    Disparada periodicamente pelo Celery Beat (ver
    ``config.settings.CELERY_BEAT_SCHEDULE``) — só faz o fan-out, não
    consulta o Zabbix ela mesma.
    """
    for sistema, configuracoes in CONFIGURACAO_BANCOS_POR_SISTEMA.items():
        if configuracoes:
            atualizar_status_banco_sistema.delay(sistema)
