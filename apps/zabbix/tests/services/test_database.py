"""Testes do serviço de status de banco de dados por sistema."""

from unittest.mock import patch

from apps.zabbix.constants import CONFIGURACAO_BANCOS_POR_SISTEMA
from apps.zabbix.constants import avaliar_mysql_ping
from apps.zabbix.constants import avaliar_psql_running
from apps.zabbix.constants import avaliar_sqlserver_running
from apps.zabbix.services.database import obter_status_banco
from apps.zabbix.services.database import sistema_configurado


class TestConfiguracaoBancosPorSistema:
    """Testes cobrindo a forma do dicionário estático de configuração."""

    def test_sistemas_conhecidos_estao_presentes(self) -> None:
        """Alguns sistemas de referência estão mapeados."""
        for sistema in ("Novo SGP", "Serap", "Serap Estudantes", "Sigla"):
            assert sistema in CONFIGURACAO_BANCOS_POR_SISTEMA

    def test_escolhas_nao_tem_banco(self) -> None:
        """O sistema "Escolhas" está mapeado explicitamente como sem banco."""
        assert CONFIGURACAO_BANCOS_POR_SISTEMA["Escolhas"] == []

    def test_novo_sgp_tem_instancias_de_escrita_e_leitura(self) -> None:
        """O sistema "Novo SGP" tem duas instâncias, com papéis distintos."""
        configuracoes = CONFIGURACAO_BANCOS_POR_SISTEMA["Novo SGP"]

        assert {cfg.role for cfg in configuracoes} == {"escrita", "leitura"}

    def test_semantica_invertida_mysql_vs_postgres(self) -> None:
        """MySQL considera "1" ok; Postgres/SQL Server considera "0" ok."""
        assert avaliar_mysql_ping("1") is True
        assert avaliar_mysql_ping("0") is False
        assert avaliar_psql_running("0") is True
        assert avaliar_psql_running("1") is False
        assert avaliar_sqlserver_running("0") is True
        assert avaliar_sqlserver_running("1") is False


class TestSistemaConfigurado:
    """Testes cobrindo sistema_configurado()."""

    def test_sistema_conhecido(self) -> None:
        """Um sistema com instâncias configuradas retorna True."""
        assert sistema_configurado("Novo SGP") is True

    def test_sistema_sem_banco(self) -> None:
        """O sistema "Escolhas" (lista vazia) retorna False."""
        assert sistema_configurado("Escolhas") is False

    def test_sistema_desconhecido(self) -> None:
        """Um sistema fora do dicionário retorna False."""
        assert sistema_configurado("Sistema Que Não Existe") is False


class TestObterStatusBanco:
    """Testes cobrindo obter_status_banco()."""

    def test_sistema_sem_banco_nao_chama_o_zabbix(self) -> None:
        """O sistema "Escolhas" responde instantâneo, sem chamar o Zabbix."""
        with patch(
            "apps.zabbix.services.database.client.zabbix_rpc"
        ) as mock_rpc:
            resultado = obter_status_banco("Escolhas")

        mock_rpc.assert_not_called()
        assert resultado == {
            "system": "Escolhas",
            "hasDatabase": False,
            "instances": [],
        }

    def test_sistema_desconhecido_nao_chama_o_zabbix(self) -> None:
        """Um sistema fora do dicionário também não chama o Zabbix."""
        with patch(
            "apps.zabbix.services.database.client.zabbix_rpc"
        ) as mock_rpc:
            resultado = obter_status_banco("Sistema Que Não Existe")

        mock_rpc.assert_not_called()
        assert resultado["hasDatabase"] is False

    def test_instancia_unica_disponivel(self) -> None:
        """Um sistema com PostgreSQL disponível reporta available=True."""
        with patch(
            "apps.zabbix.services.database.client.zabbix_rpc",
            return_value=[{"itemid": "1", "lastvalue": "0"}],
        ):
            resultado = obter_status_banco("Novo SGP")

        assert resultado["hasDatabase"] is True
        disponibilidades = {
            i["role"]: i["available"] for i in resultado["instances"]
        }
        assert disponibilidades == {"escrita": True, "leitura": True}

    def test_falha_em_uma_instancia_nao_afeta_a_outra(self) -> None:
        """Se uma instância falhar, só ela fica available=False."""

        def _zabbix_rpc_simulado(method, params):
            if params["hostids"] == "10747":  # Novo SGP (Escrita)
                raise TimeoutError("Zabbix indisponível")
            return [{"itemid": "2", "lastvalue": "0"}]

        with patch(
            "apps.zabbix.services.database.client.zabbix_rpc",
            side_effect=_zabbix_rpc_simulado,
        ):
            resultado = obter_status_banco("Novo SGP")

        disponibilidades = {
            i["role"]: i["available"] for i in resultado["instances"]
        }
        assert disponibilidades == {"escrita": False, "leitura": True}

    def test_item_ausente_resulta_em_indisponivel(self) -> None:
        """Sem nenhum item retornado, a instância fica available=False."""
        with patch(
            "apps.zabbix.services.database.client.zabbix_rpc",
            return_value=[],
        ):
            resultado = obter_status_banco("Serap")

        assert resultado["instances"][0]["available"] is False
