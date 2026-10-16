"""Testes das Celery tasks do app zabbix."""

from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.zabbix import cache as zabbix_cache
from apps.zabbix.constants import CONFIGURACAO_BANCOS_POR_SISTEMA
from apps.zabbix.tasks import atualizar_jenkins_job
from apps.zabbix.tasks import atualizar_status
from apps.zabbix.tasks import atualizar_status_banco_sistema
from apps.zabbix.tasks import atualizar_status_bancos


@pytest.fixture(autouse=True)
def _limpar_cache() -> None:
    """Garante que cada teste comece com o cache vazio."""
    cache.clear()


class TestAtualizarStatus:
    """Testes cobrindo a task atualizar_status."""

    def test_grava_o_status_no_cache(self) -> None:
        """A task grava o resultado do serviço na chave esperada."""
        status_simulado = {
            "available": True,
            "incidents_recent": False,
            "message": "Sem incidentes recentes",
        }
        with patch(
            "apps.zabbix.tasks.servico_status.obter_status",
            return_value=status_simulado,
        ) as mock_obter:
            atualizar_status("producao", "host-x", "projeto-y")

        mock_obter.assert_called_once_with("producao", "projeto-y", "host-x")
        chave = zabbix_cache.chave_status("producao", "host-x", "projeto-y")
        assert cache.get(chave) == status_simulado


class TestAtualizarJenkinsJob:
    """Testes cobrindo a task atualizar_jenkins_job."""

    def test_grava_o_resumo_no_cache(self) -> None:
        """A task grava o resumo do serviço na chave esperada."""
        resumo_simulado = {"lastBuild": {"number": 1}}
        with patch(
            "apps.zabbix.tasks.servico_jenkins.obter_resumo",
            return_value=resumo_simulado,
        ) as mock_obter:
            atualizar_jenkins_job("meu-job", "prod")

        mock_obter.assert_called_once_with("meu-job", "prod")
        chave = zabbix_cache.chave_jenkins("meu-job", "prod")
        assert cache.get(chave) == resumo_simulado


class TestAtualizarStatusBancoSistema:
    """Testes cobrindo a task atualizar_status_banco_sistema."""

    def test_grava_o_status_do_banco_no_cache(self) -> None:
        """A task grava o resultado do serviço na chave esperada."""
        status_simulado = {
            "system": "Novo SGP",
            "hasDatabase": True,
            "instances": [],
        }
        with patch(
            "apps.zabbix.tasks.servico_database.obter_status_banco",
            return_value=status_simulado,
        ) as mock_obter:
            atualizar_status_banco_sistema("Novo SGP")

        mock_obter.assert_called_once_with("Novo SGP")
        chave = zabbix_cache.chave_database("Novo SGP")
        assert cache.get(chave) == status_simulado


class TestAtualizarStatusBancos:
    """Testes cobrindo a task periódica (Beat) atualizar_status_bancos."""

    def test_dispara_uma_task_por_sistema_configurado(self) -> None:
        """Dispara a task só pros sistemas com banco configurado."""
        sistemas_com_banco = [
            sistema
            for sistema, config in CONFIGURACAO_BANCOS_POR_SISTEMA.items()
            if config
        ]
        sistemas_sem_banco = [
            sistema
            for sistema, config in CONFIGURACAO_BANCOS_POR_SISTEMA.items()
            if not config
        ]
        assert (
            sistemas_sem_banco
        ), "cenário de teste espera algum sistema vazio"

        with patch(
            "apps.zabbix.tasks.atualizar_status_banco_sistema.delay"
        ) as mock_delay:
            atualizar_status_bancos()

        assert mock_delay.call_count == len(sistemas_com_banco)
        chamados = {chamada.args[0] for chamada in mock_delay.call_args_list}
        assert chamados == set(sistemas_com_banco)
        assert not chamados & set(sistemas_sem_banco)
