"""Testes da Celery task do app bensfisicos."""

from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache

from apps.bensfisicos.constants import CHAVE_CACHE_METRICAS
from apps.bensfisicos.tasks import atualizar_metricas


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestAtualizarMetricas:
    """Testes cobrindo a task atualizar_metricas."""

    def test_grava_metricas_na_chave(self) -> None:
        """A task grava o contrato do backend na chave do Bens Físicos."""
        contrato = {"atualizado_em": "2026-11-10T10:00"}

        with patch(
            "apps.bensfisicos.client.obter_metricas", return_value=contrato
        ):
            atualizar_metricas()

        assert cache.get("bensfisicos:metricas") == contrato

    def test_usa_o_ttl_do_bens_fisicos(self) -> None:
        """O contrato expira no TTL configurado para o Bens Físicos."""
        contrato = {"atualizado_em": "2026-11-10T10:00"}

        with (
            patch(
                "apps.bensfisicos.client.obter_metricas",
                return_value=contrato,
            ),
            patch("apps.bensfisicos.tasks.cache.set") as mock_set,
        ):
            atualizar_metricas()

        mock_set.assert_called_once_with(
            CHAVE_CACHE_METRICAS,
            contrato,
            timeout=settings.BENS_FISICOS_CACHE_TTL_METRICAS_SECONDS,
        )

    def test_nao_grava_contrato_degradado(self) -> None:
        """Se o backend não leu o banco, a chave continua vazia."""
        with patch(
            "apps.bensfisicos.client.obter_metricas",
            return_value={"atualizado_em": None},
        ):
            atualizar_metricas()

        assert cache.get(CHAVE_CACHE_METRICAS) is None
