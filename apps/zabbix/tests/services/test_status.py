"""Testes do serviço de status de disponibilidade (presets producao/filas)."""

import re
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from apps.zabbix.services.status import obter_status
from apps.zabbix.services.status import status_a_partir_de_triggers

_REGEX_FORMATO_DATA = re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$")


class TestStatusAPartirDeTriggers:
    """Testes cobrindo status_a_partir_de_triggers()."""

    def test_sem_triggers(self) -> None:
        """Sem triggers, o serviço fica disponível e sem incidentes."""
        resultado = status_a_partir_de_triggers([])

        assert resultado == {
            "available": True,
            "incidents_recent": False,
            "message": "Sem incidentes recentes",
        }

    def test_trigger_ativo_usa_o_maior_lastchange(self) -> None:
        """Havendo múltiplos triggers ativos, usa o de maior lastchange."""
        triggers = [
            {"value": "1", "lastchange": "1700000000"},
            {"value": "1", "lastchange": "1700000100"},
        ]

        resultado = status_a_partir_de_triggers(triggers)

        assert resultado["available"] is False
        assert resultado["incidents_recent"] is True
        assert resultado["message"] == "Há incidentes ativos"
        esperado = datetime.fromtimestamp(
            1700000100, tz=ZoneInfo("America/Sao_Paulo")
        ).strftime("%d/%m/%Y %H:%M")
        assert resultado["lastIncidentAt"] == esperado
        assert _REGEX_FORMATO_DATA.match(resultado["lastIncidentAt"])

    def test_lastchange_invalido_e_tratado_como_zero(self) -> None:
        """Um `lastchange` não-numérico não quebra o cálculo (vira 0)."""
        triggers = [{"value": "1", "lastchange": "não-é-numero"}]

        resultado = status_a_partir_de_triggers(triggers)

        assert resultado["available"] is False
        esperado = datetime.fromtimestamp(
            0, tz=ZoneInfo("America/Sao_Paulo")
        ).strftime("%d/%m/%Y %H:%M")
        assert resultado["lastIncidentAt"] == esperado

    def test_trigger_resolvido_nao_conta_como_ativo(self) -> None:
        """Um trigger com value diferente de "1" não é um incidente ativo."""
        triggers = [{"value": "0", "lastchange": "1700000000"}]

        with patch("apps.zabbix.services.status.timezone.now") as mock_now:
            mock_now.return_value = datetime(
                2000, 1, 1, tzinfo=ZoneInfo("UTC")
            )
            resultado = status_a_partir_de_triggers(triggers)

        assert resultado["available"] is True

    def test_incidente_recente_dentro_da_janela(self, settings) -> None:
        """Um trigger resolvido, mas recente, marca incidents_recent=True."""
        settings.ZABBIX_RECENT_WINDOW_MS = 3_600_000  # 1 hora
        agora = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        lastchange = int(agora.timestamp()) - 1_800  # 30 minutos atrás

        with patch("apps.zabbix.services.status.timezone.now") as mock_now:
            mock_now.return_value = agora
            resultado = status_a_partir_de_triggers(
                [{"value": "0", "lastchange": str(lastchange)}]
            )

        assert resultado == {
            "available": True,
            "incidents_recent": True,
            "message": "Houve incidentes recentes",
            "lastIncidentAt": datetime.fromtimestamp(
                lastchange, tz=ZoneInfo("America/Sao_Paulo")
            ).strftime("%d/%m/%Y %H:%M"),
        }

    def test_incidente_fora_da_janela_nao_conta_como_recente(
        self, settings
    ) -> None:
        """Um trigger resolvido há mais tempo que a janela não é recente."""
        settings.ZABBIX_RECENT_WINDOW_MS = 3_600_000  # 1 hora
        agora = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        lastchange = int(agora.timestamp()) - 7_200  # 2 horas atrás

        with patch("apps.zabbix.services.status.timezone.now") as mock_now:
            mock_now.return_value = agora
            resultado = status_a_partir_de_triggers(
                [{"value": "0", "lastchange": str(lastchange)}]
            )

        assert resultado == {
            "available": True,
            "incidents_recent": False,
            "message": "Sem incidentes recentes",
        }

    def test_limite_exato_da_janela_conta_como_recente(self, settings) -> None:
        """No limite exato da janela (<=), o incidente ainda é recente."""
        settings.ZABBIX_RECENT_WINDOW_MS = 3_600_000  # 1 hora
        agora = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        lastchange = int(agora.timestamp()) - 3_600  # exatamente 1 hora atrás

        with patch("apps.zabbix.services.status.timezone.now") as mock_now:
            mock_now.return_value = agora
            resultado = status_a_partir_de_triggers(
                [{"value": "0", "lastchange": str(lastchange)}]
            )

        assert resultado["incidents_recent"] is True


class TestObterStatus:
    """Testes cobrindo obter_status() (integração com o client)."""

    def test_monta_parametros_do_preset_producao(self) -> None:
        """O preset producao filtra por host e description."""
        with patch(
            "apps.zabbix.services.status.client.zabbix_rpc", return_value=[]
        ) as mock_rpc:
            obter_status("producao", "meu-projeto", "meu-host")

        mock_rpc.assert_called_once_with(
            "trigger.get",
            {
                "filter": {
                    "host": ["meu-host"],
                    "description": ["meu-projeto"],
                },
                "output": "extend",
            },
        )

    def test_monta_parametros_do_preset_filas(self) -> None:
        """O preset filas usa host direto e selectFunctions."""
        with patch(
            "apps.zabbix.services.status.client.zabbix_rpc", return_value=[]
        ) as mock_rpc:
            obter_status("filas", "meu-projeto", "meu-host")

        mock_rpc.assert_called_once_with(
            "trigger.get",
            {
                "host": "meu-host",
                "output": "extend",
                "selectFunctions": "extend",
                "filter": {"description": "meu-projeto"},
            },
        )
