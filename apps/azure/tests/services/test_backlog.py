"""Testes do serviço de backlog do Azure DevOps."""

from typing import Any
from unittest.mock import patch

from apps.azure.services.backlog import calcular_metricas_bugs
from apps.azure.services.backlog import categorizar_work_items
from apps.azure.services.backlog import montar_backlog_vazio
from apps.azure.services.backlog import montar_wiql
from apps.azure.services.backlog import normalizar_filtros
from apps.azure.services.backlog import normalizar_filtros_de_listas
from apps.azure.services.backlog import obter_backlog
from apps.azure.services.backlog import primeiro_e_ultimo_dia_do_mes


def _item(
    identificador: int,
    tipo: str = "Bug",
    estado: str = "New",
    campos: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Monta um work item bruto no formato devolvido pelo Azure.

    Args:
        identificador: Id do work item.
        tipo: Valor de ``System.WorkItemType``.
        estado: Valor de ``System.State``.
        campos: Campos adicionais a mesclar em ``fields``.

    Returns:
        Work item bruto.
    """
    base: dict[str, Any] = {
        "System.Title": f"Item {identificador}",
        "System.WorkItemType": tipo,
        "System.State": estado,
    }
    base.update(campos or {})
    return {"id": identificador, "fields": base}


class TestPrimeiroEUltimoDiaDoMes:
    """Testes cobrindo a derivação do período a partir de ano/mês."""

    def test_mes_de_29_dias(self) -> None:
        """Fevereiro de ano bissexto termina no dia 29."""
        assert primeiro_e_ultimo_dia_do_mes(2024, 2) == (
            "2024-02-01",
            "2024-02-29",
        )


class TestMontarWiql:
    """Testes cobrindo a montagem da consulta WIQL."""

    def test_consulta_minima(self) -> None:
        """Sem datas nem filtros, só o projeto entra no WHERE."""
        consulta = montar_wiql("Projeto X", None, None, None)

        assert consulta == (
            "SELECT [System.Id] FROM WorkItems "
            "WHERE [System.TeamProject] = 'Projeto X' "
            "ORDER BY [System.CreatedDate] DESC"
        )

    def test_inclui_periodo_e_filtros_na_ordem_esperada(self) -> None:
        """Datas e filtros viram cláusulas na ordem do contrato."""
        consulta = montar_wiql(
            "P",
            "2026-01-01",
            "2026-01-31",
            {
                "work_item_types": ["BugFix", "HotFix"],
                "states": ["New"],
                "area_paths": ["A\\B"],
                "iteration_paths": ["S\\10", "S\\11"],
                "assigned_to": ["alguem@sme"],
                "tags": "urgente",
            },
        )

        assert "[System.CreatedDate] >= '2026-01-01'" in consulta
        assert "[System.CreatedDate] <= '2026-01-31'" in consulta
        assert "[System.WorkItemType] IN ('BugFix', 'HotFix')" in consulta
        assert "[System.State] IN ('New')" in consulta
        assert "[System.AreaPath] UNDER 'A\\B'" in consulta
        assert "[System.IterationPath] UNDER 'S\\10'" in consulta
        assert "[System.IterationPath] UNDER 'S\\11'" in consulta
        assert "[System.AssignedTo] IN ('alguem@sme')" in consulta
        assert "[System.Tags] CONTAINS 'urgente'" in consulta

    def test_escapa_aspas_simples_do_filtro(self) -> None:
        """Aspas simples são duplicadas, não encerram o literal."""
        consulta = montar_wiql("P", None, None, {"states": ["New' OR '1'='1"]})

        assert "[System.State] IN ('New'' OR ''1''=''1')" in consulta

    def test_remove_caracteres_de_controle(self) -> None:
        """Quebras de linha não passam para dentro da consulta."""
        consulta = montar_wiql("P", None, None, {"tags": "a\nb"})

        assert "CONTAINS 'ab'" in consulta

    def test_escapa_o_nome_do_projeto(self) -> None:
        """O projeto também é escapado, não só os filtros."""
        consulta = montar_wiql("O'Brien", None, None, None)

        assert "[System.TeamProject] = 'O''Brien'" in consulta


class TestNormalizarFiltros:
    """Testes cobrindo a normalização dos query params de filtro."""

    def test_separa_por_virgula_e_descarta_vazios(self) -> None:
        """Valores vazios entre vírgulas são descartados."""
        filtros = normalizar_filtros({"states": "New, Active ,,"})

        assert filtros == {"states": ["New", "Active"]}

    def test_ignora_filtros_ausentes(self) -> None:
        """Params ausentes ou vazios não entram no dicionário."""
        assert normalizar_filtros({"states": "", "tags": "  "}) == {}

    def test_mantem_tags_como_texto(self) -> None:
        """`tags` é um texto único, não uma lista."""
        assert normalizar_filtros({"tags": "urgente"}) == {"tags": "urgente"}


class TestCategorizarWorkItems:
    """Testes cobrindo a separação entre parents e children."""

    def test_separa_por_tipo(self) -> None:
        """Tipos conhecidos como pai vão para parents."""
        pais, filhos = categorizar_work_items(
            [
                _item(1, tipo="Feature"),
                _item(2, tipo="User Story"),
                _item(3, tipo="Bug"),
                _item(4, tipo="BugFix"),
            ]
        )

        assert [p["id"] for p in pais] == [1, 2]
        assert [f["id"] for f in filhos] == [3, 4]

    def test_emite_todas_as_chaves_do_contrato(self) -> None:
        """Campos ausentes viram None em vez de sumir do payload."""
        pais, filhos = categorizar_work_items([_item(7)])

        assert not pais
        assert filhos[0] == {
            "id": 7,
            "title": "Item 7",
            "state": "New",
            "work_item_type": "Bug",
            "tags": None,
            "created_by": None,
            "assigned_to": None,
            "area_path": None,
            "team_project": None,
            "iteration_path": None,
            "completed_work": None,
            "original_estimate": None,
            "start_date": None,
            "finish_date": None,
            "created_date": None,
            "changed_date": None,
            "closed_date": None,
            "parent_id": None,
            "parent_link": None,
        }

    def test_extrai_o_nome_de_exibicao(self) -> None:
        """`created_by`/`assigned_to` viram apenas o displayName."""
        _pais, filhos = categorizar_work_items(
            [
                _item(
                    1,
                    campos={
                        "System.CreatedBy": {"displayName": "Fulana"},
                        "System.AssignedTo": "texto-solto",
                    },
                )
            ]
        )

        assert filhos[0]["created_by"] == "Fulana"
        assert filhos[0]["assigned_to"] is None

    def test_extrai_o_pai_da_relacao_de_hierarquia(self) -> None:
        """A relação Hierarchy-Reverse vira parent_id e parent_link."""
        bruto = _item(1)
        bruto["relations"] = [
            {"rel": "System.LinkTypes.Related", "url": "https://x/9"},
            {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": "https://dev.azure.com/_apis/wit/workItems/42",
            },
        ]

        _pais, filhos = categorizar_work_items([bruto])

        assert filhos[0]["parent_id"] == 42
        assert filhos[0]["parent_link"].endswith("/42")

    def test_pai_sem_url_e_ignorado(self) -> None:
        """Uma relação de pai sem URL não quebra a conversão."""
        bruto = _item(1)
        bruto["relations"] = [
            {"rel": "System.LinkTypes.Hierarchy-Reverse", "url": ""}
        ]

        _pais, filhos = categorizar_work_items([bruto])

        assert filhos[0]["parent_id"] is None
        assert filhos[0]["parent_link"] is None

    def test_pai_com_url_nao_numerica_e_ignorado(self) -> None:
        """Uma URL de pai sem id numérico não quebra a conversão."""
        bruto = _item(1)
        bruto["relations"] = [
            {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": "https://dev.azure.com/_apis/wit/workItems/abc",
            }
        ]

        _pais, filhos = categorizar_work_items([bruto])

        assert filhos[0]["parent_id"] is None


class TestCalcularMetricasBugs:
    """Testes cobrindo o cálculo das métricas de bugs."""

    def test_agrupa_os_estados(self) -> None:
        """Cada estado cai no grupo correspondente."""
        metricas = calcular_metricas_bugs(
            [
                _item(1, estado="New"),
                _item(2, estado="Approved"),
                _item(3, estado="Active"),
                _item(4, estado="Testing"),
                _item(5, estado="Blocked"),
                _item(6, estado="Resolved"),
                _item(7, estado="Done"),
            ]
        )

        assert metricas["open"] == 2
        assert metricas["in_progress"] == 3
        assert metricas["resolved"] == 2
        assert metricas["total_cycle"] == 7

    def test_total_cycle_ignora_estado_desconhecido(self) -> None:
        """Estados fora do agrupamento não entram em total_cycle."""
        metricas = calcular_metricas_bugs(
            [_item(1, estado="New"), _item(2, estado="Removed")]
        )

        assert metricas["total_cycle"] == 1

    def test_tempo_medio_de_atendimento(self) -> None:
        """A média usa ResolvedDate, com fallback para ClosedDate."""
        metricas = calcular_metricas_bugs(
            [
                _item(
                    1,
                    estado="Resolved",
                    campos={
                        "System.CreatedDate": "2026-01-01T00:00:00Z",
                        "Microsoft.VSTS.Common.ResolvedDate": (
                            "2026-01-03T00:00:00Z"
                        ),
                    },
                ),
                _item(
                    2,
                    estado="Done",
                    campos={
                        "System.CreatedDate": "2026-01-01T00:00:00Z",
                        "Microsoft.VSTS.Common.ClosedDate": (
                            "2026-01-03T00:00:00Z"
                        ),
                    },
                ),
            ]
        )

        assert metricas["average_resolution"] == "2d"

    def test_sem_resolvidos_o_tempo_medio_e_nulo(self) -> None:
        """Sem itens resolvidos, average_resolution fica None."""
        metricas = calcular_metricas_bugs([_item(1, estado="New")])

        assert metricas["average_resolution"] is None

    def test_ignora_resolucao_anterior_a_criacao(self) -> None:
        """Datas incoerentes não entram na média."""
        metricas = calcular_metricas_bugs(
            [
                _item(
                    1,
                    estado="Resolved",
                    campos={
                        "System.CreatedDate": "2026-01-05T00:00:00Z",
                        "Microsoft.VSTS.Common.ResolvedDate": (
                            "2026-01-01T00:00:00Z"
                        ),
                    },
                )
            ]
        )

        assert metricas["average_resolution"] is None


class TestMontarBacklogVazio:
    """Testes cobrindo o payload de backlog vazio."""

    def test_metadata_sem_totais_e_metricas_zeradas(self) -> None:
        """O backlog vazio não traz total_parents/total_children."""
        vazio = montar_backlog_vazio("org", "proj", None, None)

        assert vazio["total_items"] == 0
        assert vazio["bug_metrics"]["average_resolution"] is None
        assert vazio["metadata"] == {
            "start_date": "none",
            "end_date": "none",
            "organization": "org",
            "project": "proj",
        }


class TestObterBacklog:
    """Testes cobrindo a orquestração completa do backlog."""

    def test_sem_ids_devolve_backlog_vazio(self) -> None:
        """Uma consulta WIQL sem resultados devolve o payload vazio."""
        with patch(
            "apps.azure.services.backlog.client.azure_request",
            return_value={"workItems": []},
        ) as mock_request:
            resultado = obter_backlog("org", "proj")

        assert mock_request.call_count == 1
        assert resultado == montar_backlog_vazio("org", "proj", None, None)

    def test_monta_o_payload_completo(self) -> None:
        """Com resultados, o payload traz totais, listas e métricas."""
        respostas = [
            {"workItems": [{"id": 1}, {"id": 2}]},
            {"value": [_item(1, tipo="Feature"), _item(2, tipo="Bug")]},
        ]

        with patch(
            "apps.azure.services.backlog.client.azure_request",
            side_effect=respostas,
        ):
            resultado = obter_backlog("org", "proj", "2026-01-01", None)

        assert resultado["total_items"] == 2
        assert len(resultado["parents"]) == 1
        assert len(resultado["children"]) == 1
        assert resultado["bug_metrics"]["open"] == 2
        assert resultado["metadata"] == {
            "start_date": "2026-01-01",
            "end_date": "none",
            "organization": "org",
            "project": "proj",
            "total_parents": 1,
            "total_children": 1,
        }

    def test_pagina_os_detalhes_em_lotes_de_200(self) -> None:
        """Mais de 200 ids viram mais de uma chamada de detalhes."""
        ids = [{"id": i} for i in range(1, 251)]
        respostas = [
            {"workItems": ids},
            {"value": [_item(i) for i in range(1, 201)]},
            {"value": [_item(i) for i in range(201, 251)]},
        ]

        with patch(
            "apps.azure.services.backlog.client.azure_request",
            side_effect=respostas,
        ) as mock_request:
            resultado = obter_backlog("org", "proj")

        assert mock_request.call_count == 3
        assert resultado["total_items"] == 250
        _args, kwargs = mock_request.call_args_list[1]
        assert len(kwargs["params"]["ids"].split(",")) == 200

    def test_descarta_itens_sem_id(self) -> None:
        """Itens malformados não entram na contagem nem nas listas."""
        respostas = [
            {"workItems": [{"id": 1}, {"semId": True}]},
            {"value": [_item(1), {"fields": {}}]},
        ]

        with patch(
            "apps.azure.services.backlog.client.azure_request",
            side_effect=respostas,
        ):
            resultado = obter_backlog("org", "proj")

        assert resultado["total_items"] == 1
        assert resultado["metadata"]["total_children"] == 1


class TestNormalizarFiltrosDeListas:
    """Testes cobrindo a normalização dos filtros do corpo do POST."""

    def test_limpa_espacos_e_descarta_vazios(self) -> None:
        """Valores em branco na lista são descartados."""
        filtros = normalizar_filtros_de_listas(
            {"states": ["New", " Active ", "", "  "]}
        )

        assert filtros == {"states": ["New", "Active"]}

    def test_produz_a_mesma_estrutura_do_get(self) -> None:
        """POST e GET equivalentes geram filtros idênticos."""
        do_post = normalizar_filtros_de_listas(
            {"work_item_types": ["BugFix", "HotFix"], "tags": "urgente"}
        )
        do_get = normalizar_filtros(
            {"work_item_types": "BugFix,HotFix", "tags": "urgente"}
        )

        assert do_post == do_get

    def test_ignora_filtros_ausentes(self) -> None:
        """Chaves ausentes ou vazias não entram no dicionário."""
        assert normalizar_filtros_de_listas({"states": [], "tags": ""}) == {}
