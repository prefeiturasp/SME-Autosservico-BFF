"""Serviço de status de disponibilidade (presets producao/filas)."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

from apps.zabbix import client
from apps.zabbix.constants import PRESETS_STATUS


def obter_status(preset: str, project: str, host: str) -> dict[str, Any]:
    """Consulta o Zabbix e monta o status de disponibilidade de um preset.

    Args:
        preset: Nome do preset (``producao`` ou ``filas``).
        project: Projeto/descrição do trigger consultado.
        host: Host do Zabbix consultado.

    Returns:
        Status de disponibilidade no formato consumido pelo frontend.
    """
    montar_parametros = PRESETS_STATUS[preset]
    params = montar_parametros(project, host)
    triggers = client.zabbix_rpc("trigger.get", params) or []
    return status_a_partir_de_triggers(triggers)


def status_a_partir_de_triggers(
    triggers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Converte triggers do Zabbix em um status de disponibilidade.

    Args:
        triggers: Triggers retornados por ``trigger.get`` (cada um com
            ``lastchange`` — segundos Unix em string — e ``value``,
            onde ``"1"`` indica problema ativo).

    Returns:
        Dicionário no formato ``ZabbixStatus`` do frontend
        (``available``, ``incidents_recent``, ``message`` e,
        opcionalmente, ``lastIncidentAt``).
    """
    if not triggers:
        return {
            "available": True,
            "incidents_recent": False,
            "message": "Sem incidentes recentes",
        }

    ativos = [t for t in triggers if t.get("value") == "1"]
    if ativos:
        ultimo = max(_lastchange(t) for t in ativos)
        return {
            "available": False,
            "incidents_recent": True,
            "message": "Há incidentes ativos",
            "lastIncidentAt": _formatar_data_hora(ultimo),
        }

    agora_ms = timezone.now().timestamp() * 1000
    janela_ms = settings.ZABBIX_RECENT_WINDOW_MS
    recentes = [
        t for t in triggers if agora_ms - _lastchange(t) * 1000 <= janela_ms
    ]
    if recentes:
        ultimo = max(_lastchange(t) for t in recentes)
        return {
            "available": True,
            "incidents_recent": True,
            "message": "Houve incidentes recentes",
            "lastIncidentAt": _formatar_data_hora(ultimo),
        }

    return {
        "available": True,
        "incidents_recent": False,
        "message": "Sem incidentes recentes",
    }


def _lastchange(trigger: dict[str, Any]) -> float:
    """Extrai ``lastchange`` (segundos Unix) de um trigger, com fallback.

    Args:
        trigger: Trigger retornado pelo Zabbix.

    Returns:
        ``lastchange`` como float, ou ``0`` se ausente/inválido.
    """
    try:
        return float(trigger.get("lastchange", 0))
    except (TypeError, ValueError):
        return 0.0


def _formatar_data_hora(segundos: float) -> str:
    """Formata um timestamp Unix (segundos) como ``DD/MM/YYYY HH:mm``.

    Usa o fuso horário configurado em ``TIME_ZONE``
    (``America/Sao_Paulo``).

    Args:
        segundos: Timestamp Unix em segundos.

    Returns:
        Data/hora formatada.
    """
    fuso = ZoneInfo(settings.TIME_ZONE)
    momento = datetime.fromtimestamp(segundos, tz=fuso)
    return momento.strftime("%d/%m/%Y %H:%M")
