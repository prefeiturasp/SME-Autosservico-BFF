"""Testes das Celery tasks do app azure."""

from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.azure import cache as azure_cache
from apps.azure.tasks import atualizar_backlog
from apps.azure.tasks import atualizar_diagnostico
from apps.azure.tasks import atualizar_projetos


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestAtualizarBacklog:
    """Testes cobrindo zabbix.atualizar_backlog."""

    def test_grava_o_resultado_na_chave_esperada(self) -> None:
        """O payload do serviço é gravado na chave lida pela view."""
        filtros = {"states": ["New"]}
        payload = {"total_items": 3}

        with patch(
            "apps.azure.tasks.servico_backlog.obter_backlog",
            return_value=payload,
        ) as mock_servico:
            atualizar_backlog("org", "proj", None, None, filtros)

        mock_servico.assert_called_once_with(
            "org", "proj", None, None, filtros
        )
        chave = azure_cache.chave_backlog("org", "proj", None, None, filtros)
        assert cache.get(chave) == payload

    def test_usa_o_periodo_na_chave(self) -> None:
        """Períodos diferentes gravam em chaves diferentes."""
        with patch(
            "apps.azure.tasks.servico_backlog.obter_backlog",
            return_value={"total_items": 0},
        ):
            atualizar_backlog("org", "proj", "2026-01-01", "2026-01-31", {})

        assert (
            cache.get(
                azure_cache.chave_backlog(
                    "org", "proj", "2026-01-01", "2026-01-31", {}
                )
            )
            is not None
        )
        assert (
            cache.get(azure_cache.chave_backlog("org", "proj", None, None, {}))
            is None
        )


class TestAtualizarProjetos:
    """Testes cobrindo azure.atualizar_projetos."""

    def test_grava_o_resultado_na_chave_esperada(self) -> None:
        """O payload do serviço é gravado na chave lida pela view."""
        payload = {"count": 2, "projects": []}

        with patch(
            "apps.azure.tasks.servico_projetos.obter_projetos",
            return_value=payload,
        ) as mock_servico:
            atualizar_projetos("org", 100, 0, None)

        mock_servico.assert_called_once_with("org", 100, 0, None)
        chave = azure_cache.chave_projetos("org", 100, 0, None)
        assert cache.get(chave) == payload

    def test_paginas_diferentes_usam_chaves_diferentes(self) -> None:
        """Cada página tem sua própria entrada de cache."""
        with patch(
            "apps.azure.tasks.servico_projetos.obter_projetos",
            return_value={"count": 0},
        ):
            atualizar_projetos("org", 100, 0, None)

        assert cache.get(azure_cache.chave_projetos("org", 100, 0, None))
        assert (
            cache.get(azure_cache.chave_projetos("org", 100, 50, None)) is None
        )


class TestAtualizarDiagnostico:
    """Testes cobrindo azure.atualizar_diagnostico."""

    def test_grava_o_resultado_na_chave_esperada(self) -> None:
        """O payload do serviço é gravado na chave lida pela view."""
        payload = {"project_name": "proj", "total_items": 3}

        with patch(
            "apps.azure.tasks.servico_diagnostico.obter_diagnostico",
            return_value=payload,
        ) as mock_servico:
            atualizar_diagnostico("org", "proj")

        mock_servico.assert_called_once_with("org", "proj")
        chave = azure_cache.chave_diagnostico("org", "proj")
        assert cache.get(chave) == payload
