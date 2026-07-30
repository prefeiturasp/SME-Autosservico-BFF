"""Testes do cache de estado da UI (BFF_BROKER) do app azure."""

from unittest.mock import MagicMock

import pytest
from django.core.cache import cache

from apps.azure.cache import chave_backlog
from apps.azure.cache import chave_diagnostico
from apps.azure.cache import chave_projetos
from apps.azure.cache import obter_ou_marcar_para_atualizar


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestChaveBacklog:
    """Testes cobrindo a geração determinística da chave do backlog."""

    def test_e_deterministica(self) -> None:
        """A mesma combinação de entrada gera sempre a mesma chave."""
        filtros = {"states": ["New"]}

        primeira = chave_backlog("org", "proj", None, None, filtros)
        segunda = chave_backlog("org", "proj", None, None, filtros)

        assert primeira == segunda

    def test_muda_com_o_projeto(self) -> None:
        """Projetos diferentes geram chaves diferentes."""
        primeira = chave_backlog("org", "proj-a", None, None, {})
        segunda = chave_backlog("org", "proj-b", None, None, {})

        assert primeira != segunda

    def test_muda_com_os_filtros(self) -> None:
        """Filtros diferentes geram chaves diferentes."""
        primeira = chave_backlog(
            "org", "proj", None, None, {"states": ["New"]}
        )
        segunda = chave_backlog(
            "org", "proj", None, None, {"states": ["Active"]}
        )

        assert primeira != segunda

    def test_muda_com_o_periodo(self) -> None:
        """Períodos diferentes geram chaves diferentes."""
        primeira = chave_backlog("org", "proj", "2026-01-01", None, {})
        segunda = chave_backlog("org", "proj", "2026-02-01", None, {})

        assert primeira != segunda

    def test_independe_da_ordem_das_chaves_de_filtro(self) -> None:
        """A mesma combinação em outra ordem resolve para a mesma chave."""
        primeira = chave_backlog(
            "org", "proj", None, None, {"states": ["New"], "tags": "x"}
        )
        segunda = chave_backlog(
            "org", "proj", None, None, {"tags": "x", "states": ["New"]}
        )

        assert primeira == segunda


class TestChavesDeProjetosEDiagnostico:
    """Testes cobrindo as demais chaves de cache do app."""

    def test_projetos_muda_com_a_pagina(self) -> None:
        """Páginas diferentes geram chaves diferentes."""
        primeira = chave_projetos("org", 100, 0, None)
        segunda = chave_projetos("org", 100, 100, None)

        assert primeira != segunda

    def test_projetos_muda_com_o_token(self) -> None:
        """Tokens de continuação diferentes geram chaves diferentes."""
        primeira = chave_projetos("org", 100, 0, None)
        segunda = chave_projetos("org", 100, 0, "tk")

        assert primeira != segunda

    def test_diagnostico_muda_com_o_projeto(self) -> None:
        """Projetos diferentes geram chaves diferentes."""
        primeira = chave_diagnostico("org", "proj-a")
        segunda = chave_diagnostico("org", "proj-b")

        assert primeira != segunda

    def test_diagnostico_nao_colide_com_backlog(self) -> None:
        """As famílias de chave usam prefixos distintos."""
        assert chave_diagnostico("org", "proj").startswith(
            "azure:diagnostico:"
        )
        assert chave_backlog("org", "proj", None, None, {}).startswith(
            "azure:backlog:"
        )


class TestObterOuMarcarParaAtualizar:
    """Testes do padrão cache-aside reexportado de ``apps.core.cache``."""

    def test_retorna_valor_cacheado_sem_disparar_tarefa(self) -> None:
        """Em cache hit, o valor é retornado e nenhuma task é disparada."""
        cache.set("azure:teste:hit", {"total_items": 1}, timeout=60)
        tarefa = MagicMock()

        resultado = obter_ou_marcar_para_atualizar(
            "azure:teste:hit", tarefa, (), ttl_lock=30
        )

        assert resultado == {"total_items": 1}
        tarefa.delay.assert_not_called()

    def test_dispara_tarefa_em_cache_frio(self) -> None:
        """Em cache miss, dispara a task e retorna None."""
        tarefa = MagicMock()

        resultado = obter_ou_marcar_para_atualizar(
            "azure:teste:miss", tarefa, ("org", "proj"), ttl_lock=30
        )

        assert resultado is None
        tarefa.delay.assert_called_once_with("org", "proj")
