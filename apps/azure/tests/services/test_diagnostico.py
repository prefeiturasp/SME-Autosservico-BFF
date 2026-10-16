"""Testes do serviço de diagnóstico do backlog do Azure DevOps."""

from typing import Any
from unittest.mock import patch

from apps.azure.services.diagnostico import montar_diagnostico
from apps.azure.services.diagnostico import montar_diagnostico_vazio
from apps.azure.services.diagnostico import obter_diagnostico


def _convertido(
    identificador: int,
    tipo: str | None = "Bug",
    estado: str = "New",
    titulo: str = "Item",
) -> dict[str, Any]:
    """Monta um work item já no formato de saída do serviço de backlog.

    Args:
        identificador: Id do work item.
        tipo: Valor de ``work_item_type``.
        estado: Valor de ``state``.
        titulo: Título do item.

    Returns:
        Work item convertido.
    """
    return {
        "id": identificador,
        "title": titulo,
        "state": estado,
        "work_item_type": tipo,
    }


class TestMontarDiagnostico:
    """Testes cobrindo a derivação do diagnóstico."""

    def test_conta_por_tipo_somando_pais_e_filhos(self) -> None:
        """A contagem cobre parents e children juntos."""
        backlog = {
            "total_items": 4,
            "parents": [_convertido(1, "Feature")],
            "children": [
                _convertido(2, "Bug"),
                _convertido(3, "Bug"),
                _convertido(4, "BugFix"),
            ],
        }

        diagnostico = montar_diagnostico("Projeto", backlog)

        assert diagnostico["total_items"] == 4
        assert diagnostico["work_item_type_counts"] == {
            "Feature": 1,
            "Bug": 2,
            "BugFix": 1,
        }

    def test_tipo_ausente_vira_unknown(self) -> None:
        """Itens sem tipo entram como Unknown."""
        backlog = {
            "total_items": 1,
            "parents": [],
            "children": [_convertido(1, None)],
        }

        diagnostico = montar_diagnostico("Projeto", backlog)

        assert diagnostico["work_item_type_counts"] == {"Unknown": 1}

    def test_amostra_limitada_a_20_itens(self) -> None:
        """A amostra traz no máximo 20 itens, parents primeiro."""
        backlog = {
            "total_items": 30,
            "parents": [_convertido(i, "Feature") for i in range(1, 6)],
            "children": [_convertido(i) for i in range(6, 31)],
        }

        diagnostico = montar_diagnostico("Projeto", backlog)

        amostra = diagnostico["sample_items"]
        assert len(amostra) == 20
        assert amostra[0]["type"] == "Feature"
        assert [item["id"] for item in amostra[:5]] == [1, 2, 3, 4, 5]

    def test_titulo_da_amostra_e_truncado_em_80(self) -> None:
        """Títulos longos são cortados em 80 caracteres."""
        backlog = {
            "total_items": 1,
            "parents": [],
            "children": [_convertido(1, titulo="x" * 200)],
        }

        diagnostico = montar_diagnostico("Projeto", backlog)

        assert len(diagnostico["sample_items"][0]["title"]) == 80


class TestMontarDiagnosticoVazio:
    """Testes cobrindo o fallback do diagnóstico."""

    def test_estrutura_do_fallback(self) -> None:
        """O fallback preserva todas as chaves do contrato."""
        assert montar_diagnostico_vazio("Projeto") == {
            "project_name": "Projeto",
            "total_items": 0,
            "work_item_type_counts": {},
            "sample_items": [],
        }


class TestObterDiagnostico:
    """Testes cobrindo a orquestração do diagnóstico."""

    def test_busca_o_backlog_sem_filtros(self) -> None:
        """O diagnóstico ignora datas e filtros de tipo."""
        backlog = {
            "total_items": 1,
            "parents": [],
            "children": [_convertido(1)],
        }

        with patch(
            "apps.azure.services.diagnostico.servico_backlog.obter_backlog",
            return_value=backlog,
        ) as mock_backlog:
            resultado = obter_diagnostico("org", "Projeto")

        mock_backlog.assert_called_once_with(
            "org", "Projeto", None, None, None
        )
        assert resultado["project_name"] == "Projeto"
        assert resultado["work_item_type_counts"] == {"Bug": 1}
