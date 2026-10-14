"""Testes das Celery tasks do app sgp."""

from typing import Any
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache

from apps.sgp.constants import chave_cache_metricas
from apps.sgp.tasks import aquecer_periodo_corrente
from apps.sgp.tasks import atualizar_metricas


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestAtualizarMetricas:
    """Testes cobrindo a task atualizar_metricas."""

    def test_grava_metricas_na_chave_do_periodo(self) -> None:
        """A task grava o contrato do backend na chave do ano/bimestre."""
        contrato: dict[str, Any] = {"ano_letivo": 2026, "bimestre": 2}

        with patch(
            "apps.sgp.client.obter_metricas", return_value=contrato
        ) as mock_obter:
            atualizar_metricas(2026, 2)

        mock_obter.assert_called_once_with(2026, 2)
        assert cache.get(chave_cache_metricas(2026, 2)) == contrato


class TestAquecerPeriodoCorrente:
    """Cobre o reaquecimento do período letivo corrente."""

    def test_aquece_o_periodo_resolvido(self) -> None:
        """Resolve o período corrente e grava o contrato no cache dele."""
        contrato: dict[str, Any] = {"ano_letivo": 2026, "bimestre": 3}

        with (
            patch("apps.sgp.periodo.periodo_corrente", return_value=(2026, 3)),
            patch("apps.sgp.client.obter_metricas", return_value=contrato),
        ):
            aquecer_periodo_corrente()

        assert cache.get(chave_cache_metricas(2026, 3)) == contrato


class TestBeatMetricas:
    """Garante que o cache é reaquecido em background antes de expirar."""

    def test_task_agendada_no_beat(self) -> None:
        """O beat dispara ``sgp.aquecer_periodo_corrente`` periodicamente."""
        agenda = settings.CELERY_BEAT_SCHEDULE.get(
            "sgp-aquecer-periodo-corrente"
        )

        assert agenda is not None
        assert agenda["task"] == "sgp.aquecer_periodo_corrente"

    def test_intervalo_menor_que_ttl(self) -> None:
        """O reaquecimento acontece antes do cache expirar (evita o zero)."""
        assert (
            settings.SGP_METRICAS_BEAT_INTERVAL_SECONDS
            < settings.SGP_CACHE_TTL_METRICAS_SECONDS
        )
