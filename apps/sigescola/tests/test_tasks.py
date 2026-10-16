"""Testes das Celery tasks do app sigescola."""

from typing import Any
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache

from apps.sigescola.constants import chave_cache_metricas
from apps.sigescola.tasks import aquecer_padrao
from apps.sigescola.tasks import atualizar_metricas

_FILTROS = {"periodo": "2026.2", "dre": "108100"}


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestAtualizarMetricas:
    """Testes cobrindo a task atualizar_metricas."""

    def test_grava_metricas_na_chave_dos_filtros(self) -> None:
        """A task grava o contrato do backend na chave dos filtros."""
        contrato: dict[str, Any] = {"atualizado_em": "2026-10-09T10:00"}

        with patch(
            "apps.sigescola.client.obter_metricas", return_value=contrato
        ) as mock_obter:
            atualizar_metricas(_FILTROS)

        mock_obter.assert_called_once_with(_FILTROS)
        assert cache.get(chave_cache_metricas(_FILTROS)) == contrato

    def test_nao_grava_contrato_degradado(self) -> None:
        """Se o backend não leu o banco, a chave continua vazia."""
        with patch(
            "apps.sigescola.client.obter_metricas",
            return_value={"atualizado_em": None},
        ):
            atualizar_metricas(_FILTROS)

        assert cache.get(chave_cache_metricas(_FILTROS)) is None


class TestAquecerPadrao:
    """Cobre o reaquecimento do cenário padrão."""

    def test_grava_na_chave_sem_filtros(self) -> None:
        """O beat consulta sem filtros e grava na chave padrão."""
        contrato: dict[str, Any] = {"atualizado_em": "2026-10-09T10:00"}

        with patch(
            "apps.sigescola.client.obter_metricas", return_value=contrato
        ) as mock_obter:
            aquecer_padrao()

        mock_obter.assert_called_once_with({})
        assert cache.get(chave_cache_metricas({})) == contrato


class TestChaveCache:
    """Cobre a chave de cache por filtros."""

    def test_estavel_e_separa_combinacoes(self) -> None:
        """Mesma chave em qualquer ordem; filtros diferentes, chaves também."""
        assert chave_cache_metricas(
            {"dre": "108100", "periodo": "2026.2"}
        ) == chave_cache_metricas(_FILTROS)
        assert chave_cache_metricas({}) != chave_cache_metricas(_FILTROS)


class TestBeatMetricas:
    """Garante que o cenário padrão é reaquecido antes de expirar."""

    def test_task_agendada_no_beat(self) -> None:
        """O beat dispara ``sigescola.aquecer_padrao`` periodicamente."""
        agenda = settings.CELERY_BEAT_SCHEDULE.get("sigescola-aquecer-padrao")

        assert agenda is not None
        assert agenda["task"] == "sigescola.aquecer_padrao"

    def test_intervalo_menor_que_ttl(self) -> None:
        """O reaquecimento acontece antes do cache expirar."""
        assert (
            settings.SIGESCOLA_METRICAS_BEAT_INTERVAL_SECONDS
            < settings.SIGESCOLA_CACHE_TTL_METRICAS_SECONDS
        )
