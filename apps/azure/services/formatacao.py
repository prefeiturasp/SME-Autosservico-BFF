"""Formatação de datas e durações do backlog do Azure DevOps.

Funções puras, sem nenhuma chamada de rede. Reproduzem exatamente o
formato de saída já consumido pelo frontend: datas em ``DD/MM/YYYY`` e
tempo médio de atendimento como rótulo pt-br pronto para exibição.
"""

import re
from datetime import datetime

from apps.azure.constants import FORMATO_DATA_SAIDA

# Só a primeira ocorrência interessa: nem a data nem o offset de fuso
# têm ponto, então a primeira fração é sempre a dos segundos.
_REGEX_FRACAO_SEGUNDOS = re.compile(r"\.(\d+)")


def _normalizar_iso(valor: str) -> str:
    """Ajusta um timestamp ISO do Azure para o que ``fromisoformat`` aceita.

    O Azure devolve o sufixo ``Z`` e, às vezes, sete dígitos de fração de
    segundo — a biblioteca padrão aceita no máximo seis.

    Args:
        valor: Timestamp ISO 8601 como veio do Azure.

    Returns:
        Timestamp normalizado.
    """
    texto = valor.strip()
    if texto.endswith(("Z", "z")):
        texto = f"{texto[:-1]}+00:00"
    return _REGEX_FRACAO_SEGUNDOS.sub(
        lambda casamento: f".{casamento.group(1)[:6]}", texto, count=1
    )


def parsear_data_iso(valor: str | None) -> datetime | None:
    """Converte um timestamp ISO do Azure em ``datetime``, sem exceções.

    Args:
        valor: Timestamp ISO 8601, ou ``None``.

    Returns:
        O ``datetime`` correspondente, ou ``None`` se ausente/inválido.
    """
    if not valor:
        return None
    try:
        return datetime.fromisoformat(_normalizar_iso(valor))
    except (TypeError, ValueError):
        return None


def formatar_data(valor: str | None) -> str | None:
    """Formata um timestamp ISO do Azure como ``DD/MM/YYYY``.

    Args:
        valor: Timestamp ISO 8601, ou ``None``.

    Returns:
        Data formatada, ou ``None`` se ausente/inválida.
    """
    momento = parsear_data_iso(valor)
    if momento is None:
        return None
    return momento.strftime(FORMATO_DATA_SAIDA)


def humanizar_duracao_horas(total_horas: float) -> tuple[float, str]:
    """Escolhe a unidade mais natural para uma duração em horas.

    Aproxima 1 mês como 30 dias e 1 ano como 365 dias.

    Args:
        total_horas: Duração total em horas.

    Returns:
        Tupla ``(valor, unidade)``, com unidade em ``minutes``,
        ``hours``, ``days``, ``months`` ou ``years``.
    """
    total_dias = total_horas / 24

    if total_horas < 1:
        return round(total_horas * 60, 1), "minutes"
    if total_horas < 24:
        return round(total_horas, 1), "hours"
    if total_dias < 30:
        return round(total_dias, 1), "days"
    if total_dias < 365:
        return round(total_dias / 30, 1), "months"
    return round(total_dias / 365, 1), "years"


def formatar_rotulo_duracao(valor: float, unidade: str) -> str:
    """Monta o rótulo pt-br do tempo de atendimento.

    Args:
        valor: Valor já convertido para a unidade.
        unidade: Unidade devolvida por ``humanizar_duracao_horas``.

    Returns:
        Rótulo pronto para exibição (ex.: ``"2d"``, ``"1,5 meses"``).
    """
    if valor == int(valor):
        numero = str(int(valor))
    else:
        numero = f"{valor:.1f}".replace(".", ",")

    if unidade == "minutes":
        return f"{numero}min"
    if unidade == "hours":
        return f"{numero}h"
    if unidade == "days":
        return f"{numero}d"
    if unidade == "months":
        return f"{numero} {'mês' if valor == 1 else 'meses'}"
    return f"{numero} {'ano' if valor == 1 else 'anos'}"
