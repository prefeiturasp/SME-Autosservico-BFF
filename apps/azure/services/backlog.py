"""Serviço de backlog de work items do Azure DevOps.

O fluxo reproduz o contrato já consumido pelo frontend: uma consulta
WIQL devolve os ids, os detalhes são buscados em lotes, os itens são
separados entre ``parents`` e ``children`` e as métricas de bugs são
calculadas sobre o conjunto retornado.
"""

import calendar
import logging
from datetime import date
from typing import Any

from apps.azure import client
from apps.azure.constants import CAMPO_AREA
from apps.azure.constants import CAMPO_ATRIBUIDO_A
from apps.azure.constants import CAMPO_CRIADO_POR
from apps.azure.constants import CAMPO_DATA_ALTERACAO
from apps.azure.constants import CAMPO_DATA_CRIACAO
from apps.azure.constants import CAMPO_DATA_FECHAMENTO
from apps.azure.constants import CAMPO_DATA_FIM
from apps.azure.constants import CAMPO_DATA_INICIO
from apps.azure.constants import CAMPO_DATA_RESOLUCAO
from apps.azure.constants import CAMPO_ESTADO
from apps.azure.constants import CAMPO_ESTIMATIVA
from apps.azure.constants import CAMPO_ITERACAO
from apps.azure.constants import CAMPO_PROJETO
from apps.azure.constants import CAMPO_TAGS
from apps.azure.constants import CAMPO_TIPO
from apps.azure.constants import CAMPO_TITULO
from apps.azure.constants import CAMPO_TRABALHO_CONCLUIDO
from apps.azure.constants import CHAVES_FILTRO_LISTA
from apps.azure.constants import ESTADOS_ABERTOS
from apps.azure.constants import ESTADOS_EM_ANDAMENTO
from apps.azure.constants import ESTADOS_RESOLVIDOS
from apps.azure.constants import FILTRO_CONTAINS
from apps.azure.constants import FILTROS_IN
from apps.azure.constants import FILTROS_IN_FINAL
from apps.azure.constants import FILTROS_UNDER
from apps.azure.constants import LIMITE_IDS_WIQL
from apps.azure.constants import RECURSO_WIQL
from apps.azure.constants import RECURSO_WORK_ITEMS
from apps.azure.constants import REGEX_CARACTERES_CONTROLE
from apps.azure.constants import RELACAO_PAI
from apps.azure.constants import TAMANHO_LOTE_WORK_ITEMS
from apps.azure.constants import TIPOS_WORK_ITEM_PAI
from apps.azure.constants import VERSAO_API
from apps.azure.services.formatacao import formatar_data
from apps.azure.services.formatacao import formatar_rotulo_duracao
from apps.azure.services.formatacao import humanizar_duracao_horas
from apps.azure.services.formatacao import parsear_data_iso

logger = logging.getLogger("bff_azure")


def primeiro_e_ultimo_dia_do_mes(ano: int, mes: int) -> tuple[str, str]:
    """Devolve o primeiro e o último dia de um mês em ``YYYY-MM-DD``.

    Args:
        ano: Ano de referência.
        mes: Mês de referência (1-12).

    Returns:
        Tupla ``(primeiro_dia, ultimo_dia)``.

    Raises:
        ValueError: Quando ``ano``/``mes`` não formam uma data válida.
    """
    primeiro = date(ano, mes, 1)
    _, ultimo_dia = calendar.monthrange(ano, mes)
    ultimo = date(ano, mes, ultimo_dia)
    return (
        primeiro.strftime("%Y-%m-%d"),
        ultimo.strftime("%Y-%m-%d"),
    )


def _literal_wiql(valor: str) -> str:
    """Escapa um valor para uso como literal de texto numa consulta WIQL.

    Aspas simples são duplicadas (a forma de escape da própria WIQL) e
    caracteres de controle são removidos, para que um valor de filtro
    vindo do frontend não consiga encerrar o literal e injetar cláusulas
    na consulta.

    Args:
        valor: Valor bruto do filtro.

    Returns:
        Valor pronto para ser interpolado entre aspas simples.
    """
    return REGEX_CARACTERES_CONTROLE.sub("", valor).replace("'", "''")


def _clausulas_de_filtros(filtros: dict[str, Any]) -> list[str]:
    """Monta as cláusulas WIQL correspondentes aos filtros informados.

    Args:
        filtros: Filtros já normalizados (listas de strings e ``tags``).

    Returns:
        Lista de cláusulas, na ordem em que compõem o ``WHERE``.
    """
    clausulas: list[str] = []

    for chave, campo in FILTROS_IN.items():
        valores = filtros.get(chave)
        if valores:
            lista = ", ".join(f"'{_literal_wiql(v)}'" for v in valores)
            clausulas.append(f"[{campo}] IN ({lista})")

    for chave, campo in FILTROS_UNDER.items():
        valores = filtros.get(chave)
        if valores:
            clausulas.extend(
                f"[{campo}] UNDER '{_literal_wiql(v)}'" for v in valores
            )

    for chave, campo in FILTROS_IN_FINAL.items():
        valores = filtros.get(chave)
        if valores:
            lista = ", ".join(f"'{_literal_wiql(v)}'" for v in valores)
            clausulas.append(f"[{campo}] IN ({lista})")

    tags = filtros.get(FILTRO_CONTAINS)
    if tags:
        clausulas.append(f"[{CAMPO_TAGS}] CONTAINS '{_literal_wiql(tags)}'")

    return clausulas


def montar_wiql(
    projeto: str,
    inicio: str | None,
    fim: str | None,
    filtros: dict[str, Any] | None,
) -> str:
    """Monta a consulta WIQL que seleciona os ids do backlog.

    Args:
        projeto: Nome do projeto no Azure DevOps.
        inicio: Data inicial (``YYYY-MM-DD``) ou ``None``.
        fim: Data final (``YYYY-MM-DD``) ou ``None``.
        filtros: Filtros adicionais já normalizados, ou ``None``.

    Returns:
        A consulta WIQL completa.
    """
    clausulas = [f"[{CAMPO_PROJETO}] = '{_literal_wiql(projeto)}'"]
    if inicio:
        clausulas.append(
            f"[{CAMPO_DATA_CRIACAO}] >= '{_literal_wiql(inicio)}'"
        )
    if fim:
        clausulas.append(f"[{CAMPO_DATA_CRIACAO}] <= '{_literal_wiql(fim)}'")
    if filtros:
        clausulas.extend(_clausulas_de_filtros(filtros))

    # A WIQL é montada por interpolação porque a API do Azure não tem
    # bind de parâmetros. Todo valor de origem externa passa antes por
    # _literal_wiql(), que duplica aspas simples e remove caracteres de
    # controle; os nomes de campo são constantes deste módulo. Daí a
    # supressão do alerta de injeção logo abaixo.
    return (
        "SELECT [System.Id] FROM WorkItems "  # noqa: S608
        f"WHERE {' AND '.join(clausulas)} "
        f"ORDER BY [{CAMPO_DATA_CRIACAO}] DESC"
    )


def _consultar_ids(
    organizacao: str,
    projeto: str,
    inicio: str | None,
    fim: str | None,
    filtros: dict[str, Any] | None,
) -> list[int]:
    """Executa a consulta WIQL e devolve os ids dos work items.

    Args:
        organizacao: Organização no Azure DevOps.
        projeto: Nome do projeto.
        inicio: Data inicial (``YYYY-MM-DD``) ou ``None``.
        fim: Data final (``YYYY-MM-DD``) ou ``None``.
        filtros: Filtros adicionais já normalizados, ou ``None``.

    Returns:
        Ids encontrados, na ordem devolvida pelo Azure.
    """
    consulta = montar_wiql(projeto, inicio, fim, filtros)
    corpo = client.azure_request(
        "POST",
        client.montar_url(organizacao, projeto, RECURSO_WIQL),
        params={
            "api-version": VERSAO_API,
            "$top": LIMITE_IDS_WIQL,
        },
        json_body={"query": consulta},
    )
    return [
        item["id"]
        for item in corpo.get("workItems", [])
        if isinstance(item, dict) and item.get("id") is not None
    ]


def _obter_detalhes(
    organizacao: str, projeto: str, ids: list[int]
) -> list[dict[str, Any]]:
    """Busca os detalhes dos work items, em lotes.

    Itens sem ``id`` são descartados: sem ele não é possível montar uma
    resposta válida, e manter o item deixaria a contagem inconsistente
    com a listagem.

    Args:
        organizacao: Organização no Azure DevOps.
        projeto: Nome do projeto.
        ids: Ids a consultar.

    Returns:
        Work items brutos, como devolvidos pelo Azure.
    """
    url = client.montar_url(organizacao, projeto, RECURSO_WORK_ITEMS)
    itens: list[dict[str, Any]] = []

    for inicio in range(0, len(ids), TAMANHO_LOTE_WORK_ITEMS):
        lote = ids[inicio : inicio + TAMANHO_LOTE_WORK_ITEMS]
        corpo = client.azure_request(
            "GET",
            url,
            params={
                "ids": ",".join(str(i) for i in lote),
                "api-version": VERSAO_API,
                "$expand": "relations",
            },
        )
        itens.extend(
            item
            for item in corpo.get("value", [])
            if isinstance(item, dict) and item.get("id") is not None
        )

    return itens


def _extrair_pai(
    relacoes: list[dict[str, Any]] | None,
) -> tuple[int | None, str | None]:
    """Extrai o id e o link do item pai a partir das relações.

    Args:
        relacoes: Relações do work item, ou ``None``.

    Returns:
        Tupla ``(parent_id, parent_link)``, ambos ``None`` se não houver
        pai ou se a URL não terminar em um id numérico.
    """
    if not relacoes:
        return None, None

    for relacao in relacoes:
        if relacao.get("rel") != RELACAO_PAI:
            continue
        url_pai = relacao.get("url", "")
        if not url_pai:
            break
        try:
            return int(url_pai.rsplit("/", maxsplit=1)[-1]), url_pai
        except ValueError:
            break

    return None, None


def _nome_exibicao(valor: Any) -> str | None:
    """Extrai ``displayName`` de um campo que pode ser dicionário ou nulo.

    Args:
        valor: Valor bruto do campo.

    Returns:
        O nome de exibição, ou ``None``.
    """
    if isinstance(valor, dict):
        nome = valor.get("displayName")
        return nome if isinstance(nome, str) else None
    return None


def _criar_work_item(item: dict[str, Any]) -> dict[str, Any]:
    """Converte um work item bruto do Azure no formato de saída.

    Todas as chaves são sempre emitidas — as ausentes viram ``None`` —
    para preservar o contrato já consumido pelo frontend.

    Args:
        item: Work item bruto devolvido pelo Azure.

    Returns:
        Work item no formato de saída.
    """
    campos = item.get("fields", {})
    id_pai, link_pai = _extrair_pai(item.get("relations"))

    return {
        "id": int(item["id"]),
        "title": campos.get(CAMPO_TITULO, ""),
        "state": campos.get(CAMPO_ESTADO),
        "work_item_type": campos.get(CAMPO_TIPO, ""),
        "tags": campos.get(CAMPO_TAGS),
        "created_by": _nome_exibicao(campos.get(CAMPO_CRIADO_POR)),
        "assigned_to": _nome_exibicao(campos.get(CAMPO_ATRIBUIDO_A)),
        "area_path": campos.get(CAMPO_AREA),
        "team_project": campos.get(CAMPO_PROJETO),
        "iteration_path": campos.get(CAMPO_ITERACAO),
        "completed_work": campos.get(CAMPO_TRABALHO_CONCLUIDO),
        "original_estimate": campos.get(CAMPO_ESTIMATIVA),
        "start_date": formatar_data(campos.get(CAMPO_DATA_INICIO)),
        "finish_date": formatar_data(campos.get(CAMPO_DATA_FIM)),
        "created_date": formatar_data(campos.get(CAMPO_DATA_CRIACAO)),
        "changed_date": formatar_data(campos.get(CAMPO_DATA_ALTERACAO)),
        "closed_date": formatar_data(campos.get(CAMPO_DATA_FECHAMENTO)),
        "parent_id": id_pai,
        "parent_link": link_pai,
    }


def categorizar_work_items(
    itens: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separa os work items entre ``parents`` e ``children``.

    Args:
        itens: Work items brutos devolvidos pelo Azure.

    Returns:
        Tupla ``(parents, children)`` já no formato de saída.
    """
    pais: list[dict[str, Any]] = []
    filhos: list[dict[str, Any]] = []

    for item in itens:
        convertido = _criar_work_item(item)
        destino = (
            pais
            if convertido["work_item_type"] in TIPOS_WORK_ITEM_PAI
            else filhos
        )
        destino.append(convertido)

    return pais, filhos


def calcular_metricas_bugs(itens: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula as métricas da seção de bugs a partir dos itens brutos.

    Considera todos os itens retornados pela consulta — o filtro de tipos
    do request já define o escopo de bugs. ``total_cycle`` é a soma dos
    três grupos de estado, e não o total de itens: itens em estados fora
    do agrupamento conhecido não entram na conta.

    Args:
        itens: Work items brutos devolvidos pelo Azure.

    Returns:
        Métricas no formato consumido pelo frontend.
    """
    abertos = 0
    em_andamento = 0
    resolvidos = 0
    horas_resolucao: list[float] = []

    for item in itens:
        campos = item.get("fields", {})

        estado = campos.get(CAMPO_ESTADO)
        if estado in ESTADOS_ABERTOS:
            abertos += 1
        elif estado in ESTADOS_EM_ANDAMENTO:
            em_andamento += 1
        elif estado in ESTADOS_RESOLVIDOS:
            resolvidos += 1

        criado_em = parsear_data_iso(campos.get(CAMPO_DATA_CRIACAO))
        resolvido_em = parsear_data_iso(
            campos.get(CAMPO_DATA_RESOLUCAO)
            or campos.get(CAMPO_DATA_FECHAMENTO)
        )
        if criado_em and resolvido_em and resolvido_em >= criado_em:
            horas_resolucao.append(
                (resolvido_em - criado_em).total_seconds() / 3600
            )

    tempo_medio = None
    if horas_resolucao:
        media = sum(horas_resolucao) / len(horas_resolucao)
        valor, unidade = humanizar_duracao_horas(media)
        tempo_medio = formatar_rotulo_duracao(valor, unidade)

    return {
        "total_cycle": abertos + em_andamento + resolvidos,
        "open": abertos,
        "in_progress": em_andamento,
        "resolved": resolvidos,
        "average_resolution": tempo_medio,
    }


def montar_backlog_vazio(
    organizacao: str,
    projeto: str,
    inicio: str | None,
    fim: str | None,
) -> dict[str, Any]:
    """Monta a resposta de backlog vazio.

    É o mesmo payload devolvido quando a consulta WIQL não encontra
    nenhum work item, e serve também como fallback seguro da view em
    cache frio — mantém o contrato do frontend intacto, sem quebrar a
    interface (diretriz 2 do C3).

    Args:
        organizacao: Organização consultada.
        projeto: Nome do projeto consultado.
        inicio: Data inicial (``YYYY-MM-DD``) ou ``None``.
        fim: Data final (``YYYY-MM-DD``) ou ``None``.

    Returns:
        Backlog vazio no formato consumido pelo frontend.
    """
    return {
        "total_items": 0,
        "parents": [],
        "children": [],
        "bug_metrics": {
            "total_cycle": 0,
            "open": 0,
            "in_progress": 0,
            "resolved": 0,
            "average_resolution": None,
        },
        "metadata": {
            "start_date": inicio or "none",
            "end_date": fim or "none",
            "organization": organizacao,
            "project": projeto,
        },
    }


def obter_backlog(
    organizacao: str,
    projeto: str,
    inicio: str | None = None,
    fim: str | None = None,
    filtros: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Consulta o Azure DevOps e monta o backlog de um projeto.

    Args:
        organizacao: Organização no Azure DevOps.
        projeto: Nome do projeto consultado.
        inicio: Data inicial (``YYYY-MM-DD``) ou ``None``.
        fim: Data final (``YYYY-MM-DD``) ou ``None``.
        filtros: Filtros adicionais já normalizados, ou ``None``.

    Returns:
        Backlog no formato consumido pelo frontend.
    """
    ids = _consultar_ids(organizacao, projeto, inicio, fim, filtros)
    if not ids:
        logger.info(
            "Azure: backlog vazio | org=%s projeto=%s", organizacao, projeto
        )
        return montar_backlog_vazio(organizacao, projeto, inicio, fim)

    itens = _obter_detalhes(organizacao, projeto, ids)
    pais, filhos = categorizar_work_items(itens)
    metricas = calcular_metricas_bugs(itens)

    logger.info(
        "Azure: backlog carregado | org=%s projeto=%s itens=%d pais=%d "
        "filhos=%d",
        organizacao,
        projeto,
        len(itens),
        len(pais),
        len(filhos),
    )

    return {
        "total_items": len(itens),
        "parents": pais,
        "children": filhos,
        "bug_metrics": metricas,
        "metadata": {
            "start_date": inicio or "none",
            "end_date": fim or "none",
            "organization": organizacao,
            "project": projeto,
            "total_parents": len(pais),
            "total_children": len(filhos),
        },
    }


def normalizar_filtros(brutos: dict[str, str]) -> dict[str, Any]:
    """Normaliza os filtros recebidos como query params.

    Valores de lista chegam separados por vírgula; entradas vazias são
    descartadas para que ``?states=`` não vire uma cláusula WIQL sem
    valor.

    Args:
        brutos: Query params relevantes, já como texto.

    Returns:
        Filtros normalizados; dicionário vazio quando nenhum foi
        informado.
    """
    filtros: dict[str, Any] = {}

    for chave in CHAVES_FILTRO_LISTA:
        valores = [
            parte.strip()
            for parte in (brutos.get(chave) or "").split(",")
            if parte.strip()
        ]
        if valores:
            filtros[chave] = valores

    tags = (brutos.get(FILTRO_CONTAINS) or "").strip()
    if tags:
        filtros[FILTRO_CONTAINS] = tags

    return filtros


def normalizar_filtros_de_listas(brutos: dict[str, Any]) -> dict[str, Any]:
    """Normaliza filtros que já chegam como listas (corpo do ``POST``).

    Produz exatamente a mesma estrutura de ``normalizar_filtros``, para
    que ``GET`` e ``POST`` equivalentes resolvam para a mesma chave de
    cache.

    Args:
        brutos: Filtros do corpo da requisição.

    Returns:
        Filtros normalizados; dicionário vazio quando nenhum foi
        informado.
    """
    filtros: dict[str, Any] = {}

    for chave in CHAVES_FILTRO_LISTA:
        valores = [
            str(valor).strip()
            for valor in (brutos.get(chave) or [])
            if str(valor).strip()
        ]
        if valores:
            filtros[chave] = valores

    tags = (brutos.get(FILTRO_CONTAINS) or "").strip()
    if tags:
        filtros[FILTRO_CONTAINS] = tags

    return filtros
