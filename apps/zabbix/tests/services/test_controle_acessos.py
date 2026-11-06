"""Testes do serviço de controle de acessos do SGP."""

from datetime import datetime
from typing import Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

from apps.zabbix.services import controle_acessos
from apps.zabbix.services.controle_acessos import estado_indisponivel
from apps.zabbix.services.controle_acessos import obter_estado_atual
from apps.zabbix.services.controle_acessos import obter_serie
from apps.zabbix.services.controle_acessos import serie_indisponivel

_FUSO = ZoneInfo("America/Sao_Paulo")
_AGORA = datetime(2026, 11, 10, 9, 30, tzinfo=_FUSO)
_RPC = "apps.zabbix.services.controle_acessos.client.zabbix_rpc"


def _ts(ano: int, mes: int, dia: int, hora: int, minuto: int) -> int:
    """Timestamp Unix de um momento no fuso de São Paulo."""
    return int(datetime(ano, mes, dia, hora, minuto, tzinfo=_FUSO).timestamp())


def _item(itemid: str, chave: str, lastvalue: str, value_type: str = "3"):
    """Item do ``item.get`` com os campos pedidos pelo serviço."""
    return {
        "itemid": itemid,
        "key_": chave,
        "value_type": value_type,
        "lastvalue": lastvalue,
    }


def _itens(**ultimos: str) -> list[dict[str, Any]]:
    """Itens do host com os últimos valores informados."""
    padrao = {
        "max.conexoes": "5000",
        "usuarios.conectados": "1346",
        "usuarios.conectados.sgp": "1300",
        "usuarios.conectados.sondagem": "46",
        "usuarios.aguardando": "0",
        "time.login": "0.8",
        "start.position.queue": "0",
    }
    padrao.update({k.replace("_", "."): v for k, v in ultimos.items()})
    return [
        _item(str(i), chave, valor, "0" if chave == "time.login" else "3")
        for i, (chave, valor) in enumerate(padrao.items(), start=1)
    ]


def _rpc_falso(
    itens: list[dict[str, Any]],
    historico: dict[str, list[tuple[int, Any]]] | None = None,
    tendencias: dict[str, list[tuple[int, Any]]] | None = None,
):
    """Simula o Zabbix por método, com histórico/tendência por itemid."""
    historico = historico or {}
    tendencias = tendencias or {}

    def rpc(metodo: str, params: dict[str, Any]) -> Any:
        if metodo == "item.get":
            return itens
        if metodo == "history.get":
            return [
                {"clock": str(c), "value": str(v)}
                for c, v in historico.get(params["itemids"], [])
                if params["time_from"] <= c <= params["time_till"]
            ]
        if metodo == "trend.get":
            return [
                {"itemid": i, "clock": str(c), "value_max": str(v)}
                for i in params["itemids"]
                for c, v in tendencias.get(i, [])
                if params["time_from"] <= c <= params["time_till"]
            ]
        raise AssertionError(metodo)

    return rpc


class TestEstadoAtual:
    """Cobre os cards: limite, conectados, fila e tempo de espera."""

    def test_sem_fila(self) -> None:
        """Sem fila, não há início de fila nem tempo de espera."""
        with patch(_RPC, side_effect=_rpc_falso(_itens())) as rpc:
            estado = obter_estado_atual(_AGORA)

        assert estado["limite_conexoes"] == 5000
        assert estado["conectados"] == {
            "total": 1346,
            "sgp": 1300,
            "sondagem": 46,
        }
        assert estado["em_fila"] == 0
        assert estado["fila_iniciada_em"] is None
        assert estado["tempo_espera_estimado"] == {
            "media_s": None,
            "posicao_media": None,
            "testes": 0,
            "atingiu_limite_teste": False,
        }
        item_get = rpc.call_args_list[0]
        assert item_get.args[1]["hostids"] == "10762"

    def test_com_fila_calcula_inicio_e_espera(self) -> None:
        """Com fila, acha o início da sequência e a média dos testes."""
        historico: dict[str, list[tuple[int, Any]]] = {
            # usuarios.aguardando (itemid 5): zerou às 07:40, fila às 07:41
            "5": [
                (_ts(2026, 11, 10, 7, 40), 0),
                (_ts(2026, 11, 10, 7, 41), 12),
                (_ts(2026, 11, 10, 9, 29), 1467),
            ],
            # time.login (6) e start.position.queue (7), mesmo clock
            "6": [
                (_ts(2026, 11, 10, 8, 40), 0.9),
                (_ts(2026, 11, 10, 8, 50), 100.0),
                (_ts(2026, 11, 10, 9, 0), 600.0),
            ],
            "7": [
                (_ts(2026, 11, 10, 8, 40), 0),
                (_ts(2026, 11, 10, 8, 50), 6),
                (_ts(2026, 11, 10, 9, 0), 10),
            ],
        }
        itens = _itens(usuarios_aguardando="1467", usuarios_conectados="6467")

        with patch(_RPC, side_effect=_rpc_falso(itens, historico)):
            estado = obter_estado_atual(_AGORA)

        assert estado["em_fila"] == 1467
        assert estado["fila_iniciada_em"] == "2026-11-10T07:41:00-03:00"
        assert estado["tempo_espera_estimado"] == {
            "media_s": 350.0,
            "posicao_media": 8,
            "testes": 2,
            "atingiu_limite_teste": True,
        }

    def test_fila_na_janela_inteira_usa_ponto_mais_antigo(self) -> None:
        """Se a fila não zerou nas últimas 24 h, usa o ponto mais antigo."""
        historico: dict[str, list[tuple[int, Any]]] = {
            "5": [
                (_ts(2026, 11, 9, 10, 0), 3),
                (_ts(2026, 11, 10, 9, 0), 4),
            ]
        }
        itens = _itens(usuarios_aguardando="4")

        with patch(_RPC, side_effect=_rpc_falso(itens, historico)):
            estado = obter_estado_atual(_AGORA)

        assert estado["fila_iniciada_em"] == "2026-11-09T10:00:00-03:00"

    def test_itens_ausentes_viram_nulos(self) -> None:
        """Sem itens no host, os campos ficam nulos (sem quebrar)."""
        with patch(_RPC, side_effect=_rpc_falso([])):
            estado = obter_estado_atual(_AGORA)

        assert estado["limite_conexoes"] is None
        assert estado["conectados"]["total"] is None
        assert estado["em_fila"] is None
        assert estado["tempo_espera_estimado"]["testes"] == 0


class TestSerie:
    """Cobre o gráfico de acessos por hora, dia, mês e ano."""

    # itemids de _itens(): 2 conectados, 3 sgp, 4 sondagem, 5 aguardando

    def test_hora_usa_o_dia_corrente(self) -> None:
        """A visão por hora só pede a tendência desde a meia-noite."""
        tendencias = {
            "2": [
                (_ts(2026, 11, 10, 7, 0), 1200),
                (_ts(2026, 11, 10, 8, 0), 5100),
            ],
            "5": [(_ts(2026, 11, 10, 8, 0), 100)],
        }

        with patch(
            _RPC, side_effect=_rpc_falso(_itens(), tendencias=tendencias)
        ) as rpc:
            serie = obter_serie("hora", _AGORA)

        trend_get = rpc.call_args_list[-1].args[1]
        assert trend_get["time_from"] == _ts(2026, 11, 10, 0, 0)
        assert serie["granularidade"] == "hora"
        assert serie["pontos"] == [
            {
                "inicio": "2026-11-10T07:00:00-03:00",
                "total": 1200,
                "em_fila_max": 0,
                "fila_ativa": False,
            },
            {
                "inicio": "2026-11-10T08:00:00-03:00",
                "total": 5100,
                "em_fila_max": 100,
                "fila_ativa": True,
            },
        ]

    def test_mes_agrega_pelo_maximo_e_soma_sistemas_antes_do_total(
        self,
    ) -> None:
        """Antes do item total, usa SGP + Sondagem; agrega pelo máximo."""
        tendencias = {
            # junho: só sgp/sondagem (item total ainda não existia)
            "3": [
                (_ts(2026, 6, 29, 10, 0), 6800),
                (_ts(2026, 6, 1, 9, 0), 10),
            ],
            "4": [(_ts(2026, 6, 29, 10, 0), 84)],
            "5": [(_ts(2026, 6, 29, 10, 0), 2540)],
            # agosto: item total
            "2": [(_ts(2026, 8, 3, 9, 0), 4142)],
        }

        with patch(
            _RPC, side_effect=_rpc_falso(_itens(), tendencias=tendencias)
        ):
            serie = obter_serie("mes", _AGORA)

        assert serie["pontos"] == [
            {
                "inicio": "2026-06-01T00:00:00-03:00",
                "total": 6884,
                "em_fila_max": 2540,
                "fila_ativa": True,
            },
            {
                "inicio": "2026-08-01T00:00:00-03:00",
                "total": 4142,
                "em_fila_max": 0,
                "fila_ativa": False,
            },
        ]

    def test_dia_e_ano_definem_a_janela(self) -> None:
        """Dia começa no 1º do mês; ano, em janeiro de 2026."""
        tendencias = {"2": [(_ts(2026, 11, 3, 10, 0), 4000)]}

        with patch(
            _RPC, side_effect=_rpc_falso(_itens(), tendencias=tendencias)
        ) as rpc:
            dia = obter_serie("dia", _AGORA)
            inicio_dia = rpc.call_args_list[-1].args[1]["time_from"]
            ano = obter_serie("ano", _AGORA)
            inicio_ano = rpc.call_args_list[-1].args[1]["time_from"]

        assert inicio_dia == _ts(2026, 11, 1, 0, 0)
        assert inicio_ano == _ts(2026, 1, 1, 0, 0)
        assert dia["pontos"][0]["inicio"] == "2026-11-03T00:00:00-03:00"
        assert ano["pontos"][0]["inicio"] == "2026-01-01T00:00:00-03:00"

    def test_sem_itens_nao_consulta_tendencia(self) -> None:
        """Sem itens no host, a série é vazia e não chama ``trend.get``."""
        with patch(_RPC, side_effect=_rpc_falso([])) as rpc:
            serie = obter_serie("mes", _AGORA)

        assert serie["pontos"] == []
        assert [c.args[0] for c in rpc.call_args_list] == ["item.get"]


class TestFallbacks:
    """Cobre os contratos de cache frio."""

    def test_estado_indisponivel(self) -> None:
        """Todos os campos do estado ficam nulos."""
        assert set(estado_indisponivel().values()) == {None}

    def test_serie_indisponivel(self) -> None:
        """A série fica vazia, ecoando a granularidade."""
        assert serie_indisponivel("dia") == {
            "granularidade": "dia",
            "atualizado_em": None,
            "pontos": [],
        }

    def test_valores_invalidos_viram_nulos(self) -> None:
        """Valores não numéricos do Zabbix não quebram a conversão."""
        assert controle_acessos._numero("abc") is None
        assert controle_acessos._inteiro("") is None
