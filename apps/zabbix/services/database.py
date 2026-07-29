"""Serviço de status de banco de dados por sistema."""

import logging
from typing import Any

from apps.zabbix import client
from apps.zabbix.constants import CONFIGURACAO_BANCOS_POR_SISTEMA
from apps.zabbix.constants import ConfiguracaoInstanciaBanco

logger = logging.getLogger("bff_zabbix")


def sistema_configurado(sistema: str) -> bool:
    """Indica se um sistema tem instâncias de banco monitoradas no Zabbix.

    Args:
        sistema: Nome de exibição do sistema.

    Returns:
        ``True`` quando o sistema está no dicionário de configuração e
        tem ao menos uma instância configurada.
    """
    return bool(CONFIGURACAO_BANCOS_POR_SISTEMA.get(sistema))


def obter_status_banco(sistema: str) -> dict[str, Any]:
    """Consulta o Zabbix e monta o status de banco de dados de um sistema.

    Cada instância é consultada isoladamente — uma falha em uma
    instância não afeta as demais, só marca ``available=False``
    naquela instância específica.

    Args:
        sistema: Nome de exibição do sistema (chave de
            ``CONFIGURACAO_BANCOS_POR_SISTEMA``).

    Returns:
        Status de banco de dados no formato consumido pelo frontend.
    """
    configuracoes = CONFIGURACAO_BANCOS_POR_SISTEMA.get(sistema) or []
    if not configuracoes:
        return {"system": sistema, "hasDatabase": False, "instances": []}

    instancias = [_consultar_instancia(sistema, cfg) for cfg in configuracoes]
    return {"system": sistema, "hasDatabase": True, "instances": instancias}


def _consultar_instancia(
    sistema: str, cfg: ConfiguracaoInstanciaBanco
) -> dict[str, Any]:
    """Consulta uma única instância de banco no Zabbix.

    Args:
        sistema: Nome de exibição do sistema (só para log).
        cfg: Configuração da instância a consultar.

    Returns:
        Status da instância — ``available=False`` se a consulta falhar.
    """
    instancia: dict[str, Any] = {
        "label": cfg.label,
        "dbType": cfg.db_type,
        "available": False,
    }
    if cfg.role:
        instancia["role"] = cfg.role

    try:
        itens = client.zabbix_rpc(
            "item.get",
            {
                "hostids": cfg.hostid,
                "search": {"key_": cfg.key},
                "output": ["itemid", "lastvalue"],
            },
        )
        lastvalue = itens[0].get("lastvalue", "") if itens else ""
        instancia["available"] = cfg.avaliar_disponibilidade(lastvalue)
    except Exception as exc:  # isolamento por instância
        logger.warning(
            "Zabbix: falha ao consultar %s (%s): %s", cfg.label, sistema, exc
        )

    return instancia
