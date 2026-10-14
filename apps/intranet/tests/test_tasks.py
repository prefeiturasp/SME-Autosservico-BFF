"""Testes das Celery tasks do app intranet."""

from typing import Any
from unittest.mock import call
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache

from apps.intranet.constants import PERIODOS
from apps.intranet.constants import chave_cache_metricas
from apps.intranet.tasks import aquecer_periodos
from apps.intranet.tasks import atualizar_metricas


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestAtualizarMetricas:
    """Testes cobrindo a task atualizar_metricas."""

    def test_grava_metricas_na_chave_do_recorte(self) -> None:
        """A task grava o contrato do backend na chave do período/mês."""
        contrato: dict[str, Any] = {
            "atualizado_em": "2026-10-09T13:39:51+00:00",
            "periodo": "mes",
            "mes": "2026-09",
        }

        with patch(
            "apps.intranet.client.obter_metricas", return_value=contrato
        ) as mock_obter:
            atualizar_metricas("mes", "2026-09")

        mock_obter.assert_called_once_with("mes", "2026-09")
        assert cache.get(chave_cache_metricas("mes", "2026-09")) == contrato

    def test_nao_grava_contrato_vazio_do_backend(self) -> None:
        """Sem ``atualizado_em`` (falha no banco), o cache fica frio."""
        contrato: dict[str, Any] = {
            "atualizado_em": None,
            "periodo": "geral",
            "mes": None,
            "kpis": None,
        }

        with patch(
            "apps.intranet.client.obter_metricas", return_value=contrato
        ):
            atualizar_metricas("geral", None)

        assert cache.get(chave_cache_metricas("geral", None)) is None


class TestAquecerPeriodos:
    """Cobre o reaquecimento dos períodos (fan-out do beat)."""

    def test_dispara_uma_task_por_periodo_sem_mes(self) -> None:
        """Dispara ``atualizar_metricas`` para cada período, sem mês."""
        with patch(
            "apps.intranet.tasks.atualizar_metricas.delay"
        ) as mock_delay:
            aquecer_periodos()

        assert mock_delay.call_args_list == [
            call(periodo, None) for periodo in PERIODOS
        ]


class TestBeatMetricas:
    """Garante que o cache é reaquecido em background antes de expirar."""

    def test_task_agendada_no_beat(self) -> None:
        """O beat dispara ``intranet.aquecer_periodos`` periodicamente."""
        agenda = settings.CELERY_BEAT_SCHEDULE.get("intranet-aquecer-periodos")

        assert agenda is not None
        assert agenda["task"] == "intranet.aquecer_periodos"

    def test_intervalo_menor_que_ttl(self) -> None:
        """O reaquecimento acontece antes do cache expirar (evita o zero)."""
        assert (
            settings.INTRANET_METRICAS_BEAT_INTERVAL_SECONDS
            < settings.INTRANET_CACHE_TTL_METRICAS_SECONDS
        )
