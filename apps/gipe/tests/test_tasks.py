"""Testes das Celery tasks do app gipe."""

from datetime import date
from typing import Any
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache

from apps.gipe.constants import ano_letivo_corrente
from apps.gipe.constants import chave_cache_metricas
from apps.gipe.tasks import aquecer_ano_corrente
from apps.gipe.tasks import atualizar_metricas


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestAtualizarMetricas:
    """Testes cobrindo a task atualizar_metricas."""

    def test_grava_metricas_na_chave_do_ano(self) -> None:
        """A task grava o contrato do backend na chave do ano letivo."""
        contrato: dict[str, Any] = {
            "atualizado_em": "2026-10-27T10:00",
            "ano_letivo": 2026,
        }

        with patch(
            "apps.gipe.client.obter_metricas", return_value=contrato
        ) as mock_obter:
            atualizar_metricas(2026)

        mock_obter.assert_called_once_with(2026)
        assert cache.get("gipe:metricas:2026") == contrato

    def test_usa_o_ttl_do_gipe(self) -> None:
        """O contrato expira no TTL configurado para o GIPE."""
        contrato = {"atualizado_em": "2026-10-27T10:00"}

        with (
            patch("apps.gipe.client.obter_metricas", return_value=contrato),
            patch("apps.gipe.tasks.cache.set") as mock_set,
        ):
            atualizar_metricas(2026)

        mock_set.assert_called_once_with(
            "gipe:metricas:2026",
            contrato,
            timeout=settings.GIPE_CACHE_TTL_METRICAS_SECONDS,
        )

    def test_nao_grava_contrato_degradado(self) -> None:
        """Se o backend não leu o banco, a chave continua vazia."""
        with patch(
            "apps.gipe.client.obter_metricas",
            return_value={"atualizado_em": None},
        ):
            atualizar_metricas(2026)

        assert cache.get(chave_cache_metricas(2026)) is None


class TestAquecerAnoCorrente:
    """Cobre o reaquecimento do ano corrente."""

    def test_usa_o_ano_corrente_da_execucao(self) -> None:
        """O ano é calculado a cada execução do beat, não na importação."""
        with (
            patch("apps.gipe.tasks.ano_letivo_corrente", return_value=2027),
            patch("apps.gipe.tasks.atualizar_metricas") as mock_atualizar,
        ):
            aquecer_ano_corrente()

        mock_atualizar.assert_called_once_with(2027)


class TestConstantes:
    """Cobre a chave de cache e o ano corrente."""

    def test_chave_por_ano(self) -> None:
        """Cada ano letivo tem a sua chave."""
        assert chave_cache_metricas(2026) == "gipe:metricas:2026"

    def test_ano_corrente_pela_data_local(self) -> None:
        """O ano corrente vem da data local do servidor."""
        with patch(
            "apps.gipe.constants.timezone.localdate",
            return_value=date(2027, 1, 2),
        ):
            assert ano_letivo_corrente() == 2027


class TestBeatMetricas:
    """Garante que o ano corrente é reaquecido antes de expirar."""

    def test_task_agendada_no_beat(self) -> None:
        """O beat dispara ``gipe.aquecer_ano_corrente`` periodicamente."""
        agenda = settings.CELERY_BEAT_SCHEDULE.get("gipe-aquecer-ano-corrente")

        assert agenda is not None
        assert agenda["task"] == "gipe.aquecer_ano_corrente"

    def test_intervalo_menor_que_ttl(self) -> None:
        """O reaquecimento acontece antes do cache expirar."""
        assert (
            settings.GIPE_METRICAS_BEAT_INTERVAL_SECONDS
            < settings.GIPE_CACHE_TTL_METRICAS_SECONDS
        )
