"""Testes das Celery tasks do app sgp."""

from typing import Any
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache

from apps.sgp.constants import CHAVE_CACHE_PERIODOS
from apps.sgp.constants import chave_cache_metricas
from apps.sgp.tasks import aquecer_periodo_corrente
from apps.sgp.tasks import atualizar_metricas
from apps.sgp.tasks import atualizar_periodos


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
            atualizar_metricas(2026, "eja", 2, 1)

        mock_obter.assert_called_once_with(2026, "eja", 2, 1)
        assert cache.get(chave_cache_metricas(2026, "eja", 2, 1)) == contrato


class TestAtualizarPeriodos:
    """Testes cobrindo a task atualizar_periodos."""

    def test_grava_periodos_no_cache(self) -> None:
        """A task grava as opções de período do backend no cache."""
        contrato: dict[str, Any] = {"periodos": []}

        with patch("apps.sgp.client.obter_periodos", return_value=contrato):
            atualizar_periodos()

        assert cache.get(CHAVE_CACHE_PERIODOS) == contrato

    def test_ttl_proprio(self) -> None:
        """As opções de período têm TTL configurável próprio."""
        assert settings.SGP_CACHE_TTL_PERIODOS_SECONDS > 0


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

        chave = chave_cache_metricas(2026, "fundamental_medio", None, 3)
        assert cache.get(chave) == contrato


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
