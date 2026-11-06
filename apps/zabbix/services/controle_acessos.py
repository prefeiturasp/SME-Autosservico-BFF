"""Controle de acessos do SGP, lido do host ``monitor-fila-novosgp``.

Mesmas consultas do dashboard "NovoSGP - Controle de acessos" no Zabbix.
O hub não registra a espera de cada usuário, então o tempo médio é
estimado pelos testes sintéticos de login que caíram na fila.
"""

from datetime import datetime
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.zabbix import client
from apps.zabbix.constants import ANO_INICIO_SERIE_ACESSOS
from apps.zabbix.constants import CHAVE_AGUARDANDO
from apps.zabbix.constants import CHAVE_CONECTADOS
from apps.zabbix.constants import CHAVE_CONECTADOS_SGP
from apps.zabbix.constants import CHAVE_CONECTADOS_SONDAGEM
from apps.zabbix.constants import CHAVE_LIMITE_CONEXOES
from apps.zabbix.constants import CHAVE_POSICAO_FILA_TESTE
from apps.zabbix.constants import CHAVE_TEMPO_LOGIN_TESTE
from apps.zabbix.constants import CHAVES_CONTROLE_ACESSOS_SGP
from apps.zabbix.constants import HOSTID_CONTROLE_ACESSOS_SGP
from apps.zabbix.constants import JANELA_INICIO_FILA_SEGUNDOS
from apps.zabbix.constants import JANELA_TEMPO_ESPERA_SEGUNDOS
from apps.zabbix.constants import LIMITE_TESTE_LOGIN_SEGUNDOS

Item = dict[str, Any]


def _fuso() -> ZoneInfo:
    """Fuso dos agrupamentos e das datas devolvidas."""
    return ZoneInfo(settings.TIME_ZONE)


def _agora(agora: datetime | None) -> datetime:
    """Agora, no fuso configurado."""
    return (agora or datetime.now(tz=_fuso())).astimezone(_fuso())


def _numero(valor: Any) -> float | None:
    """Converte um valor do Zabbix em número, ou ``None`` se ausente."""
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _inteiro(valor: Any) -> int | None:
    """Converte um valor do Zabbix em inteiro, ou ``None`` se ausente."""
    numero = _numero(valor)
    return None if numero is None else round(numero)


def _itens_por_chave() -> dict[str, Item]:
    """Busca os itens do controle de acessos, indexados pela chave."""
    itens = client.zabbix_rpc(
        "item.get",
        {
            "output": ["itemid", "key_", "value_type", "lastvalue"],
            "hostids": HOSTID_CONTROLE_ACESSOS_SGP,
            "filter": {"key_": list(CHAVES_CONTROLE_ACESSOS_SGP)},
        },
    )
    return {item["key_"]: item for item in itens or []}


def _historico(
    item: Item | None, desde: datetime, ate: datetime
) -> list[tuple[int, float]]:
    """Histórico bruto ``(clock, valor)`` de um item, em ordem crescente."""
    if not item:
        return []
    linhas = client.zabbix_rpc(
        "history.get",
        {
            "output": ["clock", "value"],
            "history": int(item.get("value_type", 0)),
            "itemids": item["itemid"],
            "time_from": int(desde.timestamp()),
            "time_till": int(ate.timestamp()),
            "sortfield": "clock",
            "sortorder": "ASC",
        },
    )
    return [
        (int(linha["clock"]), valor)
        for linha in linhas or []
        if (valor := _numero(linha.get("value"))) is not None
    ]


def _inicio_da_fila(historico: list[tuple[int, float]]) -> str | None:
    """Quando a fila atual começou (ou o ponto mais antigo, se nunca zerou)."""
    inicio: int | None = None
    for clock, valor in reversed(historico):
        if valor <= 0:
            break
        inicio = clock
    if inicio is None:
        return None
    return datetime.fromtimestamp(inicio, tz=_fuso()).isoformat()


def _tempo_espera_estimado(
    tempos: list[tuple[int, float]], posicoes: list[tuple[int, float]]
) -> dict[str, Any]:
    """Média do tempo de login dos testes que entraram na fila.

    Os dois itens chegam com o mesmo ``clock``, então dá pra parear por ele.
    """
    posicao_por_clock = dict(posicoes)
    na_fila = [
        (tempo, posicao_por_clock[clock])
        for clock, tempo in tempos
        if posicao_por_clock.get(clock, 0) > 0
    ]
    if not na_fila:
        return {
            "media_s": None,
            "posicao_media": None,
            "testes": 0,
            "atingiu_limite_teste": False,
        }
    return {
        "media_s": round(sum(t for t, _ in na_fila) / len(na_fila), 1),
        "posicao_media": round(sum(p for _, p in na_fila) / len(na_fila)),
        "testes": len(na_fila),
        "atingiu_limite_teste": any(
            t >= LIMITE_TESTE_LOGIN_SEGUNDOS for t, _ in na_fila
        ),
    }


def obter_estado_atual(agora: datetime | None = None) -> dict[str, Any]:
    """Estado atual do controle de acessos.

    Args:
        agora: Momento de referência (para testes); padrão, agora.

    Returns:
        Limite, conectados, fila e tempo de espera estimado.
    """
    referencia = _agora(agora)
    itens = _itens_por_chave()

    def ultimo(chave: str) -> int | None:
        return _inteiro((itens.get(chave) or {}).get("lastvalue"))

    em_fila = ultimo(CHAVE_AGUARDANDO)
    fila_iniciada_em = None
    if em_fila:
        fila_iniciada_em = _inicio_da_fila(
            _historico(
                itens.get(CHAVE_AGUARDANDO),
                referencia - timedelta(seconds=JANELA_INICIO_FILA_SEGUNDOS),
                referencia,
            )
        )

    desde_testes = referencia - timedelta(seconds=JANELA_TEMPO_ESPERA_SEGUNDOS)
    tempo_espera = _tempo_espera_estimado(
        _historico(
            itens.get(CHAVE_TEMPO_LOGIN_TESTE), desde_testes, referencia
        ),
        _historico(
            itens.get(CHAVE_POSICAO_FILA_TESTE), desde_testes, referencia
        ),
    )

    return {
        "atualizado_em": referencia.isoformat(),
        "limite_conexoes": ultimo(CHAVE_LIMITE_CONEXOES),
        "conectados": {
            "total": ultimo(CHAVE_CONECTADOS),
            "sgp": ultimo(CHAVE_CONECTADOS_SGP),
            "sondagem": ultimo(CHAVE_CONECTADOS_SONDAGEM),
        },
        "em_fila": em_fila,
        "fila_iniciada_em": fila_iniciada_em,
        "tempo_espera_estimado": tempo_espera,
    }


def _janela(granularidade: str, agora: datetime) -> datetime:
    """Início da janela: hoje, mês corrente, ano corrente ou 2026."""
    hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularidade == "hora":
        return hoje
    if granularidade == "dia":
        return hoje.replace(day=1)
    if granularidade == "mes":
        return hoje.replace(month=1, day=1)
    return hoje.replace(year=ANO_INICIO_SERIE_ACESSOS, month=1, day=1)


def _inicio_do_ponto(momento: datetime, granularidade: str) -> datetime:
    """Trunca um momento no início do ponto do gráfico."""
    momento = momento.replace(minute=0, second=0, microsecond=0)
    if granularidade == "hora":
        return momento
    momento = momento.replace(hour=0)
    if granularidade == "dia":
        return momento
    momento = momento.replace(day=1)
    if granularidade == "mes":
        return momento
    return momento.replace(month=1)


def _maximos_por_hora(
    itens: dict[str, Item], desde: datetime, ate: datetime
) -> dict[str, dict[int, float]]:
    """Máximo por hora de cada item, por chave e ``clock``."""
    chave_por_itemid = {
        item["itemid"]: chave
        for chave, item in itens.items()
        if chave
        in (
            CHAVE_CONECTADOS,
            CHAVE_CONECTADOS_SGP,
            CHAVE_CONECTADOS_SONDAGEM,
            CHAVE_AGUARDANDO,
        )
    }
    if not chave_por_itemid:
        return {}
    tendencias = client.zabbix_rpc(
        "trend.get",
        {
            "output": ["itemid", "clock", "value_max"],
            "itemids": list(chave_por_itemid),
            "time_from": int(desde.timestamp()),
            "time_till": int(ate.timestamp()),
        },
    )
    maximos: dict[str, dict[int, float]] = {}
    for linha in tendencias or []:
        chave = chave_por_itemid.get(linha["itemid"])
        valor = _numero(linha.get("value_max"))
        if chave and valor is not None:
            maximos.setdefault(chave, {})[int(linha["clock"])] = valor
    return maximos


def _total_da_hora(maximos: dict[str, dict[int, float]], clock: int) -> float:
    """Conectados na hora.

    O item total só existe desde 28/07/2026. Antes disso, soma SGP e Sondagem.
    """
    total = maximos.get(CHAVE_CONECTADOS, {}).get(clock)
    if total is not None:
        return total
    return maximos.get(CHAVE_CONECTADOS_SGP, {}).get(clock, 0) + maximos.get(
        CHAVE_CONECTADOS_SONDAGEM, {}
    ).get(clock, 0)


def obter_serie(
    granularidade: str, agora: datetime | None = None
) -> dict[str, Any]:
    """Série do gráfico de acessos.

    Cada ponto é o pico de conectados no intervalo e indica se teve fila.

    Args:
        granularidade: ``hora``, ``dia``, ``mes`` ou ``ano``.
        agora: Momento de referência (para testes); padrão, agora.

    Returns:
        ``{"granularidade", "atualizado_em", "pontos": [...]}``.
    """
    referencia = _agora(agora)
    maximos = _maximos_por_hora(
        _itens_por_chave(), _janela(granularidade, referencia), referencia
    )
    horas = sorted(
        set(maximos.get(CHAVE_CONECTADOS, {}))
        | set(maximos.get(CHAVE_CONECTADOS_SGP, {}))
        | set(maximos.get(CHAVE_CONECTADOS_SONDAGEM, {}))
    )

    pontos: dict[datetime, dict[str, Any]] = {}
    for clock in horas:
        inicio = _inicio_do_ponto(
            datetime.fromtimestamp(clock, tz=_fuso()), granularidade
        )
        ponto = pontos.setdefault(inicio, {"total": 0.0, "em_fila_max": 0.0})
        ponto["total"] = max(ponto["total"], _total_da_hora(maximos, clock))
        ponto["em_fila_max"] = max(
            ponto["em_fila_max"],
            maximos.get(CHAVE_AGUARDANDO, {}).get(clock, 0),
        )

    return {
        "granularidade": granularidade,
        "atualizado_em": referencia.isoformat(),
        "pontos": [
            {
                "inicio": inicio.isoformat(),
                "total": round(ponto["total"]),
                "em_fila_max": round(ponto["em_fila_max"]),
                "fila_ativa": ponto["em_fila_max"] > 0,
            }
            for inicio, ponto in sorted(pontos.items())
        ],
    }


def estado_indisponivel() -> dict[str, Any]:
    """Fallback do estado atual (cache frio), sem chamada de rede."""
    return {
        "atualizado_em": None,
        "limite_conexoes": None,
        "conectados": None,
        "em_fila": None,
        "fila_iniciada_em": None,
        "tempo_espera_estimado": None,
    }


def serie_indisponivel(granularidade: str) -> dict[str, Any]:
    """Fallback da série (cache frio), sem chamada de rede."""
    return {
        "granularidade": granularidade,
        "atualizado_em": None,
        "pontos": [],
    }
