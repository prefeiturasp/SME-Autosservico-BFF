"""Serviço de resumo de build do Jenkins, via ``item.get`` do Zabbix.

O Zabbix não fala com o Jenkins diretamente aqui — outro sistema já
coleta os dados do Jenkins e grava um resumo em JSON no ``lastvalue``
de um item "dependente" do Zabbix (``type == TIPO_ITEM_JENKINS``). Este
módulo só lê esse item já coletado.
"""

import json
import math
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any
from typing import Literal
from zoneinfo import ZoneInfo

from django.conf import settings

from apps.zabbix import client
from apps.zabbix.constants import CANDIDATOS_HOMOLOG_FIXOS
from apps.zabbix.constants import HOSTIDS_JENKINS_PADRAO
from apps.zabbix.constants import REGEX_AMBIENTE_HOMOLOG
from apps.zabbix.constants import TIPO_ITEM_JENKINS

_REGEX_PROD = re.compile(r"prod", re.IGNORECASE)


class LastvalueInvalidoError(Exception):
    """JSON malformado no campo ``lastvalue`` de um item do Zabbix."""


def obter_resumo(
    project_full_name: str,
    ambiente: Literal["prod", "homolog"] = "prod",
    hostids: str = HOSTIDS_JENKINS_PADRAO,
) -> dict[str, Any]:
    """Resolve o resumo de build de um job do Jenkins via item.get do Zabbix.

    Estratégias, na ordem: (1) ``prod`` tenta a chave exata do projeto
    primeiro; se não encontrar (ou se ambiente não for "homolog"), cai
    no caminho de compatibilidade (chave ``<project>/master``, depois
    o melhor candidato por prefixo, sem filtro de ambiente); (2)
    ``homolog`` tenta uma lista fixa de ambientes candidatos e, se
    nenhum bater, busca o melhor candidato por prefixo cujo ambiente
    (extraído do próprio ``lastvalue``) seja reconhecido como homolog.

    Args:
        project_full_name: Nome/caminho do job (chave usada no item do
            Zabbix), ex.: ``"SME-NovoSGP-Docs/master"``.
        ambiente: ``"prod"`` (default) ou ``"homolog"``.
        hostids: Hostids do Zabbix a consultar.

    Returns:
        Dicionário com ``lastBuild``/``lastSuccessfulBuild``/
        ``lastFailedBuild`` (cada um ausente se não encontrado), ou
        ``{}`` se nada for encontrado ou o projeto for vazio.
    """
    project = project_full_name.strip()
    if not project:
        return {}

    if ambiente == "prod":
        direto = _tentar_buscar_resumo_por_chave(hostids, project)
        if direto:
            return direto

    if ambiente == "homolog":
        return _obter_resumo_homolog(project, hostids) or {}

    return _obter_resumo_compat(project, hostids) or {}


def resumo_a_partir_de_lastvalue(lastvalue: str | None) -> dict[str, Any]:
    """Converte o ``lastvalue`` de um item do Zabbix em um resumo de build.

    Args:
        lastvalue: Valor bruto do item (JSON serializado, array com 1
            elemento).

    Returns:
        Dicionário com os builds parseados (só as chaves encontradas),
        ou ``{}`` se ``lastvalue`` vazio ou não representar um job.

    Raises:
        LastvalueInvalidoError: Quando ``lastvalue`` não é JSON válido.
    """
    if not lastvalue:
        return {}

    try:
        analisado = json.loads(lastvalue)
    except (ValueError, TypeError) as exc:
        raise LastvalueInvalidoError(
            "Campo lastvalue inválido (JSON malformado)"
        ) from exc

    if not isinstance(analisado, list) or not analisado:
        return {}
    job = analisado[0]
    if not isinstance(job, dict):
        return {}

    resumo: dict[str, Any] = {}
    ultimo = _parsear_build(job.get("lastBuild"), "UNKNOWN")
    if ultimo:
        resumo["lastBuild"] = ultimo
    ultimo_sucesso = _parsear_build(job.get("lastSuccessfulBuild"), "SUCCESS")
    if ultimo_sucesso:
        resumo["lastSuccessfulBuild"] = ultimo_sucesso
    ultimo_falho = _parsear_build(job.get("lastFailedBuild"), "FAILURE")
    if ultimo_falho:
        resumo["lastFailedBuild"] = ultimo_falho
    return resumo


def _resumo_seguro_a_partir_de_lastvalue(
    lastvalue: str,
) -> dict[str, Any] | None:
    """Como ``resumo_a_partir_de_lastvalue``, mas nunca propaga exceção.

    Usada para candidatos (chave exata ou prefixo) onde um item com
    ``lastvalue`` malformado não deve interromper a busca pelos
    demais candidatos.

    Args:
        lastvalue: Valor bruto do item.

    Returns:
        O resumo parseado, ou ``None`` se malformado.
    """
    try:
        return resumo_a_partir_de_lastvalue(lastvalue)
    except LastvalueInvalidoError:
        return None


def _para_float(valor: object) -> float:
    """Converte um valor arbitrário em float, sem levantar exceção.

    Args:
        valor: Valor bruto (tipicamente vindo de um JSON já decodificado).

    Returns:
        O valor convertido, ou ``NaN`` se não for conversível.
    """
    try:
        return float(valor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float("nan")


def _parsear_build(build: Any, status_padrao: str) -> dict[str, Any] | None:
    """Converte um objeto de build bruto do Jenkins num formato compacto.

    Args:
        build: Objeto de build bruto (``lastBuild``/etc. do JSON).
        status_padrao: Status a usar quando o build não trouxer
            ``result`` nem estiver em andamento.

    Returns:
        Dicionário compacto do build, ou ``None`` se campos essenciais
        estiverem ausentes/inválidos.
    """
    if not isinstance(build, dict):
        return None

    numero = _para_float(build.get("number"))
    timestamp_ms = _para_float(build.get("timestamp"))
    duracao_ms = _para_float(build.get("duration"))

    if not (
        math.isfinite(numero)
        and math.isfinite(timestamp_ms)
        and math.isfinite(duracao_ms)
    ):
        return None

    resultado = build.get("result")
    resultado = resultado if isinstance(resultado, str) else None
    em_andamento = (
        build.get("inProgress") is True or build.get("building") is True
    )
    status = resultado or ("IN_PROGRESS" if em_andamento else status_padrao)

    return {
        "number": int(numero),
        "status": status,
        "timestampMs": timestamp_ms,
        "timestamp": _formatar_data_hora_de_milissegundos(timestamp_ms),
        "durationMs": duracao_ms,
        "duration": _formatar_duracao(duracao_ms),
    }


def _pontuar_resumo(resumo: dict[str, Any]) -> float:
    """Pontua um resumo pelo timestamp mais recente entre seus builds.

    Args:
        resumo: Resumo já parseado (``lastBuild``/etc.).

    Returns:
        O maior ``timestampMs`` entre os builds presentes, ou
        ``-inf`` se nenhum build válido estiver presente.
    """
    timestamps = [
        resumo.get(chave, {}).get("timestampMs")
        for chave in ("lastBuild", "lastSuccessfulBuild", "lastFailedBuild")
    ]
    finitos = [
        t
        for t in timestamps
        if isinstance(t, int | float) and math.isfinite(t)
    ]
    return max(finitos) if finitos else float("-inf")


def _ambiente_a_partir_de_lastvalue(lastvalue: str) -> str | None:
    """Extrai o ambiente (2º segmento de ``fullName``) do lastvalue.

    Nunca propaga exceção — usada só para filtrar candidatos.

    Args:
        lastvalue: Valor bruto do item.

    Returns:
        O 2º segmento de ``fullName`` (ex.: ``"homolog"`` em
        ``"projeto/homolog"``), ou ``None`` se indisponível.
    """
    try:
        analisado = json.loads(lastvalue)
    except (ValueError, TypeError):
        return None
    if not isinstance(analisado, list) or not analisado:
        return None
    job = analisado[0]
    if not isinstance(job, dict):
        return None
    nome_completo = job.get("fullName")
    if not isinstance(nome_completo, str):
        return None
    partes = nome_completo.split("/")
    return partes[1] if len(partes) >= 2 else None


def _ambiente_e_homolog(ambiente: str | None) -> bool:
    """Indica se um nome de ambiente é reconhecido como homolog.

    Args:
        ambiente: Nome do ambiente extraído do lastvalue.

    Returns:
        ``True`` se ``ambiente`` bater com ``REGEX_AMBIENTE_HOMOLOG``.
    """
    if not ambiente:
        return False
    return bool(REGEX_AMBIENTE_HOMOLOG.match(ambiente))


def _obter_base_e_ambiente_atual(project: str) -> tuple[str, str | None]:
    """Separa o projeto em ``base`` (1º segmento) e o restante do caminho.

    Args:
        project: Nome/caminho do projeto (ex.: ``"foo/prod-sp"``).

    Returns:
        Tupla ``(base, ambiente_atual)`` — ``ambiente_atual`` é
        ``None`` quando ``project`` não tem ``/``.
    """
    if "/" in project:
        base, _separador, resto = project.partition("/")
        return base, resto
    return project, None


def _montar_candidatos_homolog(ambiente_atual: str | None) -> list[str]:
    """Monta a lista ordenada de ambientes candidatos para homolog.

    Args:
        ambiente_atual: Ambiente atual do projeto (ex.: ``"prod-sp"``),
            ou ``None``.

    Returns:
        Lista de candidatos, na ordem de tentativa (troca de "prod"
        primeiro, quando aplicável, seguida da lista fixa).
    """
    candidatos: list[str] = []
    if ambiente_atual and _REGEX_PROD.search(ambiente_atual):
        candidatos.append(_REGEX_PROD.sub("homolog", ambiente_atual))
        candidatos.append(_REGEX_PROD.sub("hml", ambiente_atual))
    candidatos.extend(CANDIDATOS_HOMOLOG_FIXOS)
    return candidatos


def _melhor_resumo_entre_candidatos(
    candidatos: list[dict[str, Any]],
    permitido: Callable[[str], bool],
) -> dict[str, Any] | None:
    """Escolhe o candidato com o build mais recente, entre os permitidos.

    Args:
        candidatos: Itens retornados por ``item.get`` (cada um com
            ``lastvalue``).
        permitido: Predicado que decide se o ``lastvalue`` de um
            candidato pode ser considerado.

    Returns:
        O resumo com maior pontuação entre os candidatos válidos, ou
        ``None`` se nenhum for válido.
    """
    melhor: dict[str, Any] | None = None
    melhor_pontuacao = float("-inf")

    for candidato in candidatos:
        lastvalue = candidato.get("lastvalue")
        if not lastvalue or not permitido(lastvalue):
            continue
        resumo = _resumo_seguro_a_partir_de_lastvalue(lastvalue)
        if not resumo:
            continue
        pontuacao = _pontuar_resumo(resumo)
        if pontuacao <= melhor_pontuacao:
            continue
        melhor_pontuacao = pontuacao
        melhor = resumo

    return (
        melhor
        if melhor is not None and math.isfinite(melhor_pontuacao)
        else None
    )


def _obter_resumo_homolog(project: str, hostids: str) -> dict[str, Any] | None:
    """Resolve o resumo de build no ambiente homolog.

    Args:
        project: Nome/caminho do projeto.
        hostids: Hostids do Zabbix a consultar.

    Returns:
        O resumo encontrado, ou ``None``.
    """
    base, ambiente_atual = _obter_base_e_ambiente_atual(project)
    candidatos_ambiente = _montar_candidatos_homolog(ambiente_atual)

    for ambiente in candidatos_ambiente:
        resumo = _tentar_buscar_resumo_por_chave(hostids, f"{base}/{ambiente}")
        if resumo:
            return resumo

    candidatos = _buscar_candidatos_por_prefixo(hostids, base)
    return _melhor_resumo_entre_candidatos(
        candidatos,
        lambda lastvalue: _ambiente_e_homolog(
            _ambiente_a_partir_de_lastvalue(lastvalue)
        ),
    )


def _obter_resumo_compat(project: str, hostids: str) -> dict[str, Any] | None:
    """Resolve o resumo de build no caminho de compatibilidade (legado).

    Args:
        project: Nome/caminho do projeto (só aplicável quando não tem
            ``/`` — projetos já qualificados usam o caminho ``prod``).
        hostids: Hostids do Zabbix a consultar.

    Returns:
        O resumo encontrado, ou ``None``.
    """
    if "/" in project:
        return None

    com_master = _tentar_buscar_resumo_por_chave(hostids, f"{project}/master")
    if com_master:
        return com_master

    candidatos = _buscar_candidatos_por_prefixo(hostids, project)
    return _melhor_resumo_entre_candidatos(candidatos, lambda _lastvalue: True)


def _tentar_buscar_resumo_por_chave(
    hostids: str, chave_valor: str
) -> dict[str, Any] | None:
    """Busca o item pela chave exata e parseia o resumo, se encontrado.

    Args:
        hostids: Hostids do Zabbix a consultar.
        chave_valor: Valor exato usado na chave do item
            (``jenkins.job.mb.get[<chave_valor>]``).

    Returns:
        O resumo parseado, ou ``None`` se não encontrado/malformado.
    """
    lastvalue = _buscar_por_chave(hostids, chave_valor)
    if not lastvalue:
        return None
    return _resumo_seguro_a_partir_de_lastvalue(lastvalue)


def _buscar_por_chave(hostids: str, chave_valor: str) -> str | None:
    """Busca um item do Zabbix pela chave exata.

    Args:
        hostids: Hostids do Zabbix a consultar.
        chave_valor: Valor exato usado na chave do item.

    Returns:
        O ``lastvalue`` do item, ou ``None`` se não encontrado.
    """
    params = {
        "output": ["lastvalue"],
        "hostids": hostids,
        "search": {"key_": f"jenkins.job.mb.get[{chave_valor}]"},
        "filter": {"type": TIPO_ITEM_JENKINS},
    }
    resultado = client.zabbix_rpc("item.get", params)
    if not resultado:
        return None
    return resultado[0].get("lastvalue")  # type: ignore[no-any-return]


def _buscar_candidatos_por_prefixo(
    hostids: str, prefixo: str
) -> list[dict[str, Any]]:
    """Busca itens do Zabbix cuja chave comece pelo prefixo informado.

    Args:
        hostids: Hostids do Zabbix a consultar.
        prefixo: Prefixo da chave (ex.: nome base do projeto).

    Returns:
        Lista de itens encontrados (pode ser vazia).
    """
    params = {
        "output": ["lastvalue"],
        "hostids": hostids,
        "search": {"key_": f"jenkins.job.mb.get[{prefixo}/"},
        "filter": {"type": TIPO_ITEM_JENKINS},
    }
    return client.zabbix_rpc("item.get", params) or []


def _formatar_data_hora_de_milissegundos(ms: float) -> str:
    """Formata um timestamp Unix (milissegundos) como ``DD/MM/YYYY HH:mm``.

    Args:
        ms: Timestamp Unix em milissegundos.

    Returns:
        Data/hora formatada, no fuso configurado em ``TIME_ZONE``.
    """
    fuso = ZoneInfo(settings.TIME_ZONE)
    momento = datetime.fromtimestamp(ms / 1000, tz=fuso)
    return momento.strftime("%d/%m/%Y %H:%M")


def _formatar_duracao(ms: float) -> str:
    """Formata uma duração em milissegundos como ``Xh Ym Zs``.

    Args:
        ms: Duração em milissegundos.

    Returns:
        Duração formatada, omitindo unidades zeradas à esquerda (ex.:
        ``"5m 3s"`` quando não há horas).
    """
    total_segundos = int(ms // 1000)
    horas, resto = divmod(total_segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    if horas > 0:
        return f"{horas}h {minutos}m {segundos}s"
    if minutos > 0:
        return f"{minutos}m {segundos}s"
    return f"{segundos}s"
