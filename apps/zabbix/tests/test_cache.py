"""Testes do cache de estado da UI (BFF_BROKER) do app zabbix."""

from unittest.mock import MagicMock

import pytest
from django.core.cache import cache

from apps.zabbix.cache import chave_database
from apps.zabbix.cache import chave_jenkins
from apps.zabbix.cache import chave_status
from apps.zabbix.cache import obter_ou_marcar_para_atualizar


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestChavesDeCache:
    """Testes cobrindo a geração determinística de chaves de cache."""

    def test_chave_status_e_deterministica(self) -> None:
        """A mesma combinação de entrada gera sempre a mesma chave."""
        chave_1 = chave_status("producao", "host-x", "projeto-y")
        chave_2 = chave_status("producao", "host-x", "projeto-y")

        assert chave_1 == chave_2

    def test_chave_status_muda_com_o_projeto(self) -> None:
        """Projetos diferentes geram chaves diferentes."""
        chave_1 = chave_status("producao", "host-x", "projeto-y")
        chave_2 = chave_status("producao", "host-x", "projeto-z")

        assert chave_1 != chave_2

    def test_chave_jenkins_muda_com_o_ambiente(self) -> None:
        """Ambientes diferentes geram chaves diferentes pro mesmo projeto."""
        chave_prod = chave_jenkins("meu-job", "prod")
        chave_homolog = chave_jenkins("meu-job", "homolog")

        assert chave_prod != chave_homolog

    def test_chave_database_muda_com_o_sistema(self) -> None:
        """Sistemas diferentes geram chaves diferentes."""
        chave_1 = chave_database("Novo SGP")
        chave_2 = chave_database("Serap")

        assert chave_1 != chave_2


class TestObterOuMarcarParaAtualizar:
    """Testes cobrindo o padrão cache-aside com lock de atualização."""

    def test_retorna_valor_cacheado_sem_disparar_tarefa(self) -> None:
        """Em cache hit, o valor é retornado e nenhuma task é disparada."""
        chave = "zabbix:teste:hit"
        cache.set(chave, {"available": True}, timeout=60)
        tarefa = MagicMock()

        resultado = obter_ou_marcar_para_atualizar(
            chave, tarefa, (), ttl_lock=30
        )

        assert resultado == {"available": True}
        tarefa.delay.assert_not_called()

    def test_dispara_tarefa_em_cache_frio(self) -> None:
        """Em cache miss, dispara a task e retorna None."""
        chave = "zabbix:teste:miss"
        tarefa = MagicMock()

        resultado = obter_ou_marcar_para_atualizar(
            chave, tarefa, ("arg-1", "arg-2"), ttl_lock=30
        )

        assert resultado is None
        tarefa.delay.assert_called_once_with("arg-1", "arg-2")

    def test_nao_duplica_disparo_com_lock_ja_ocupado(self) -> None:
        """Uma segunda chamada, com o lock já ocupado, não dispara de novo."""
        chave = "zabbix:teste:concorrente"
        tarefa = MagicMock()

        primeiro = obter_ou_marcar_para_atualizar(
            chave, tarefa, (), ttl_lock=30
        )
        segundo = obter_ou_marcar_para_atualizar(
            chave, tarefa, (), ttl_lock=30
        )

        assert primeiro is None
        assert segundo is None
        tarefa.delay.assert_called_once()
