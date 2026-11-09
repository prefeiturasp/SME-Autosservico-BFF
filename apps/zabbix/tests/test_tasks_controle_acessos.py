"""Testes das Celery tasks do controle de acessos do SGP."""

from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache

from apps.zabbix import cache as zabbix_cache
from apps.zabbix.tasks import atualizar_controle_acessos
from apps.zabbix.tasks import atualizar_serie_controle_acessos


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestAtualizarControleAcessos:
    """Testes cobrindo a task atualizar_controle_acessos."""

    def test_grava_o_estado_no_cache(self) -> None:
        """A task grava o estado atual na chave do controle de acessos."""
        estado = {"limite_conexoes": 5000}
        with patch(
            "apps.zabbix.tasks.servico_controle_acessos.obter_estado_atual",
            return_value=estado,
        ):
            atualizar_controle_acessos()

        assert cache.get(zabbix_cache.chave_controle_acessos()) == estado


class TestAtualizarSerieControleAcessos:
    """Testes cobrindo a task atualizar_serie_controle_acessos."""

    @pytest.mark.parametrize(
        ("granularidade", "ttl"),
        [
            ("hora", "ZABBIX_CACHE_TTL_SERIE_ACESSOS_HORA_SECONDS"),
            ("mes", "ZABBIX_CACHE_TTL_SERIE_ACESSOS_SECONDS"),
        ],
    )
    def test_grava_a_serie_com_ttl_da_granularidade(
        self, granularidade: str, ttl: str
    ) -> None:
        """A visão por hora expira antes das demais."""
        serie = {"granularidade": granularidade, "pontos": []}
        with (
            patch(
                "apps.zabbix.tasks.servico_controle_acessos.obter_serie",
                return_value=serie,
            ) as mock_obter,
            patch("apps.zabbix.tasks.cache.set") as mock_set,
        ):
            atualizar_serie_controle_acessos(granularidade)

        mock_obter.assert_called_once_with(granularidade)
        mock_set.assert_called_once_with(
            zabbix_cache.chave_serie_acessos(granularidade),
            serie,
            timeout=getattr(settings, ttl),
        )


class TestBeatControleAcessos:
    """Garante a atualização do estado a cada minuto, antes de expirar."""

    def test_task_agendada_no_beat(self) -> None:
        """O beat dispara ``zabbix.atualizar_controle_acessos``."""
        agenda = settings.CELERY_BEAT_SCHEDULE.get(
            "zabbix-atualizar-controle-acessos"
        )

        assert agenda is not None
        assert agenda["task"] == "zabbix.atualizar_controle_acessos"

    def test_intervalo_menor_que_ttl(self) -> None:
        """O estado é renovado antes do cache expirar."""
        assert (
            settings.ZABBIX_CONTROLE_ACESSOS_BEAT_INTERVAL_SECONDS
            < settings.ZABBIX_CACHE_TTL_CONTROLE_ACESSOS_SECONDS
        )
