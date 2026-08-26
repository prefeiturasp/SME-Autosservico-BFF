"""Testes das Celery tasks do app sigpae."""

from typing import Any
from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.sigpae.constants import CHAVE_CACHE_METRICAS
from apps.sigpae.tasks import atualizar_metricas


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestAtualizarMetricas:
    """Testes cobrindo a task atualizar_metricas."""

    def test_grava_metricas_no_cache(self) -> None:
        """A task grava o contrato do backend na chave esperada."""
        contrato: dict[str, Any] = {"atualizado_em": None, "usuarios": {}}

        with patch(
            "apps.sigpae.client.obter_metricas", return_value=contrato
        ) as mock_obter:
            atualizar_metricas()

        mock_obter.assert_called_once_with()
        assert cache.get(CHAVE_CACHE_METRICAS) == contrato
