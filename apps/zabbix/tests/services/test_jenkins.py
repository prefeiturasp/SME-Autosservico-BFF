"""Testes do serviço de resumo de build do Jenkins."""

import json
from unittest.mock import patch

import pytest

from apps.zabbix.constants import CANDIDATOS_HOMOLOG_FIXOS
from apps.zabbix.services.jenkins import LastvalueInvalidoError
from apps.zabbix.services.jenkins import _ambiente_a_partir_de_lastvalue
from apps.zabbix.services.jenkins import _ambiente_e_homolog
from apps.zabbix.services.jenkins import _melhor_resumo_entre_candidatos
from apps.zabbix.services.jenkins import _parsear_build
from apps.zabbix.services.jenkins import obter_resumo
from apps.zabbix.services.jenkins import resumo_a_partir_de_lastvalue


def _build_bruto(**overrides: object) -> dict:
    """Monta um objeto de build bruto (formato do Jenkins) para os testes."""
    build = {
        "number": 42,
        "timestamp": 1_700_000_000_000,
        "duration": 60_000,
        "result": "SUCCESS",
    }
    build.update(overrides)
    return build


class TestParsearBuild:
    """Testes cobrindo _parsear_build()."""

    def test_build_valido(self) -> None:
        """Um build válido é convertido para o formato compacto."""
        resultado = _parsear_build(_build_bruto(), "UNKNOWN")

        assert resultado is not None
        assert resultado == {
            "number": 42,
            "status": "SUCCESS",
            "timestampMs": 1_700_000_000_000.0,
            "timestamp": resultado["timestamp"],
            "durationMs": 60_000.0,
            "duration": "1m 0s",
        }

    def test_build_none(self) -> None:
        """``None`` no lugar do build retorna ``None``."""
        assert _parsear_build(None, "UNKNOWN") is None

    def test_build_sem_number_retorna_none(self) -> None:
        """Campo ``number`` ausente/inválido descarta o build."""
        build = _build_bruto()
        del build["number"]

        assert _parsear_build(build, "UNKNOWN") is None

    def test_building_em_andamento_sem_result(self) -> None:
        """Sem `result`, mas com `building=True`, o status é IN_PROGRESS."""
        build = _build_bruto(building=True)
        del build["result"]

        resultado = _parsear_build(build, "UNKNOWN")

        assert resultado is not None
        assert resultado["status"] == "IN_PROGRESS"

    def test_sem_result_nem_em_andamento_usa_fallback(self) -> None:
        """Sem `result` e sem estar em andamento, usa o status padrão."""
        build = _build_bruto()
        del build["result"]

        resultado = _parsear_build(build, "MEU_FALLBACK")

        assert resultado is not None
        assert resultado["status"] == "MEU_FALLBACK"

    def test_duracao_curta_so_com_segundos(self) -> None:
        """Uma duração menor que 1 minuto aparece só como "Zs"."""
        build = _build_bruto(duration=5_000)  # 5s

        resultado = _parsear_build(build, "UNKNOWN")

        assert resultado is not None
        assert resultado["duration"] == "5s"

    def test_duracao_com_horas_e_formatada_corretamente(self) -> None:
        """Uma duração de mais de 1h aparece como "Xh Ym Zs"."""
        build = _build_bruto(duration=3_725_000)  # 1h 2m 5s

        resultado = _parsear_build(build, "UNKNOWN")

        assert resultado is not None
        assert resultado["duration"] == "1h 2m 5s"

    def test_timestamp_infinito_retorna_none(self) -> None:
        """Um timestamp infinito descarta o build."""
        build = _build_bruto(timestamp=float("inf"))

        assert _parsear_build(build, "UNKNOWN") is None

    def test_timestamp_invalido_retorna_none(self) -> None:
        """Timestamp não-numérico descarta o build."""
        build = _build_bruto(timestamp="não-é-numero")

        assert _parsear_build(build, "UNKNOWN") is None


class TestResumoAPartirDeLastvalue:
    """Testes cobrindo resumo_a_partir_de_lastvalue()."""

    def test_lastvalue_vazio_ou_none(self) -> None:
        """Sem lastvalue, o resumo é vazio."""
        assert resumo_a_partir_de_lastvalue("") == {}
        assert resumo_a_partir_de_lastvalue(None) == {}

    def test_json_malformado_levanta_erro(self) -> None:
        """JSON malformado levanta LastvalueInvalidoError."""
        with pytest.raises(LastvalueInvalidoError):
            resumo_a_partir_de_lastvalue("{isso não é json")

    def test_nao_e_lista_retorna_vazio(self) -> None:
        """Um JSON válido, mas que não é uma lista, retorna vazio."""
        assert resumo_a_partir_de_lastvalue(json.dumps({"a": 1})) == {}

    def test_lista_vazia_retorna_vazio(self) -> None:
        """Uma lista vazia retorna vazio."""
        assert resumo_a_partir_de_lastvalue(json.dumps([])) == {}

    def test_item_nao_e_objeto_retorna_vazio(self) -> None:
        """O primeiro elemento não sendo um objeto retorna vazio."""
        assert resumo_a_partir_de_lastvalue(json.dumps(["texto"])) == {}

    def test_monta_os_tres_builds(self) -> None:
        """Os três builds são montados quando presentes."""
        job = {
            "lastBuild": _build_bruto(number=3),
            "lastSuccessfulBuild": _build_bruto(number=2),
            "lastFailedBuild": _build_bruto(number=1),
        }

        resultado = resumo_a_partir_de_lastvalue(json.dumps([job]))

        assert resultado["lastBuild"]["number"] == 3
        assert resultado["lastSuccessfulBuild"]["number"] == 2
        assert resultado["lastFailedBuild"]["number"] == 1

    def test_builds_ausentes_nao_aparecem_no_resultado(self) -> None:
        """Builds ausentes não viram chaves com valor None no resultado."""
        job = {"lastBuild": _build_bruto()}

        resultado = resumo_a_partir_de_lastvalue(json.dumps([job]))

        assert "lastSuccessfulBuild" not in resultado
        assert "lastFailedBuild" not in resultado


class TestAmbienteAPartirDeLastvalue:
    """Testes cobrindo _ambiente_a_partir_de_lastvalue()."""

    def test_nunca_propaga_excecao(self) -> None:
        """JSON malformado retorna None, nunca propaga exceção."""
        assert _ambiente_a_partir_de_lastvalue("{isso não é json") is None

    def test_extrai_segundo_segmento_do_fullname(self) -> None:
        """O ambiente é o segundo segmento de fullName."""
        lastvalue = json.dumps([{"fullName": "meu-job/homolog"}])

        assert _ambiente_a_partir_de_lastvalue(lastvalue) == "homolog"

    def test_fullname_sem_segundo_segmento_retorna_none(self) -> None:
        """Sem um segundo segmento em fullName, retorna None."""
        lastvalue = json.dumps([{"fullName": "meu-job"}])

        assert _ambiente_a_partir_de_lastvalue(lastvalue) is None

    def test_nao_e_lista_retorna_none(self) -> None:
        """Um JSON válido, mas que não é lista, retorna None."""
        assert _ambiente_a_partir_de_lastvalue(json.dumps({"a": 1})) is None

    def test_job_nao_e_objeto_retorna_none(self) -> None:
        """O primeiro elemento não sendo um objeto retorna None."""
        assert _ambiente_a_partir_de_lastvalue(json.dumps(["texto"])) is None

    def test_fullname_nao_e_string_retorna_none(self) -> None:
        """`fullName` de tipo inesperado retorna None."""
        lastvalue = json.dumps([{"fullName": 123}])

        assert _ambiente_a_partir_de_lastvalue(lastvalue) is None


class TestAmbienteEHomolog:
    """Testes cobrindo _ambiente_e_homolog()."""

    @pytest.mark.parametrize(
        "ambiente", ["homolog", "HOMOLOG", "hml", "hmg", "dev", "staging"]
    )
    def test_ambientes_reconhecidos(self, ambiente: str) -> None:
        """Ambientes conhecidos (case-insensitive) são reconhecidos."""
        assert _ambiente_e_homolog(ambiente) is True

    def test_ambiente_none(self) -> None:
        """``None`` não é um ambiente de homolog."""
        assert _ambiente_e_homolog(None) is False

    def test_ambiente_desconhecido(self) -> None:
        """Um ambiente fora da lista não é reconhecido."""
        assert _ambiente_e_homolog("producao") is False


class TestMelhorResumoEntreCandidatos:
    """Testes cobrindo _melhor_resumo_entre_candidatos()."""

    def test_ignora_candidato_malformado_e_pior_apos_melhor(self) -> None:
        """Candidatos malformados e piores (após o melhor) são ignorados."""
        melhor = json.dumps(
            [{"lastBuild": _build_bruto(number=99, timestamp=9_000)}]
        )
        pior = json.dumps(
            [{"lastBuild": _build_bruto(number=1, timestamp=1_000)}]
        )
        candidatos = [
            {"lastvalue": "{isso não é json"},
            {"lastvalue": melhor},
            {"lastvalue": pior},
        ]

        resultado = _melhor_resumo_entre_candidatos(
            candidatos, lambda _lastvalue: True
        )

        assert resultado is not None
        assert resultado["lastBuild"]["number"] == 99

    def test_sem_candidatos_validos_retorna_none(self) -> None:
        """Sem nenhum candidato válido, retorna None."""
        candidatos = [{"lastvalue": ""}, {"lastvalue": "{isso não é json"}]

        resultado = _melhor_resumo_entre_candidatos(
            candidatos, lambda _lastvalue: True
        )

        assert resultado is None


class TestObterResumo:
    """Testes cobrindo obter_resumo() — as 3 estratégias de resolução."""

    def test_projeto_vazio_nao_chama_zabbix(self) -> None:
        """Projeto vazio/espaços retorna vazio sem chamar o Zabbix."""
        with patch(
            "apps.zabbix.services.jenkins.client.zabbix_rpc"
        ) as mock_rpc:
            resultado = obter_resumo("   ", "prod")

        mock_rpc.assert_not_called()
        assert resultado == {}

    def test_prod_chave_direta(self) -> None:
        """No ambiente prod, a chave exata do projeto é tentada primeiro."""
        lastvalue = json.dumps([{"lastBuild": _build_bruto()}])
        with patch(
            "apps.zabbix.services.jenkins.client.zabbix_rpc",
            return_value=[{"lastvalue": lastvalue}],
        ) as mock_rpc:
            resultado = obter_resumo("meu-job", "prod")

        assert resultado["lastBuild"]["number"] == 42
        assert mock_rpc.call_count == 1

    def test_prod_cai_para_master_quando_chave_direta_nao_acha(self) -> None:
        """Sem a chave direta, tenta `<project>/master`."""
        lastvalue = json.dumps([{"lastBuild": _build_bruto()}])

        def _rpc(_method: str, params: dict) -> list:
            chave = params["search"]["key_"]
            if chave == "jenkins.job.mb.get[meu-job/master]":
                return [{"lastvalue": lastvalue}]
            return []

        with patch(
            "apps.zabbix.services.jenkins.client.zabbix_rpc", side_effect=_rpc
        ):
            resultado = obter_resumo("meu-job", "prod")

        assert resultado["lastBuild"]["number"] == 42

    def test_prod_projeto_ja_qualificado_nao_usa_compat(self) -> None:
        """Com "/" no projeto, o caminho compat não se aplica."""
        with patch(
            "apps.zabbix.services.jenkins.client.zabbix_rpc",
            return_value=[],
        ) as mock_rpc:
            resultado = obter_resumo("meu-job/prod-sp", "prod")

        assert resultado == {}
        assert mock_rpc.call_count == 1

    def test_prod_melhor_candidato_por_prefixo(self) -> None:
        """Sem chave direta nem master, escolhe o candidato mais recente."""
        antigo = json.dumps(
            [{"lastBuild": _build_bruto(number=1, timestamp=1_000)}]
        )
        novo = json.dumps(
            [{"lastBuild": _build_bruto(number=2, timestamp=2_000)}]
        )

        def _rpc(_method: str, params: dict) -> list:
            chave = params["search"]["key_"]
            if chave == "jenkins.job.mb.get[meu-job/":
                return [{"lastvalue": antigo}, {"lastvalue": novo}]
            return []

        with patch(
            "apps.zabbix.services.jenkins.client.zabbix_rpc", side_effect=_rpc
        ):
            resultado = obter_resumo("meu-job", "prod")

        assert resultado["lastBuild"]["number"] == 2

    def test_homolog_troca_prod_por_homolog_primeiro(self) -> None:
        """Se o ambiente atual tem "prod", tenta a troca antes da lista."""
        lastvalue = json.dumps([{"lastBuild": _build_bruto()}])

        def _rpc(_method: str, params: dict) -> list:
            chave = params["search"]["key_"]
            if chave == "jenkins.job.mb.get[meu-job/homolog-sp]":
                return [{"lastvalue": lastvalue}]
            return []

        with patch(
            "apps.zabbix.services.jenkins.client.zabbix_rpc", side_effect=_rpc
        ):
            resultado = obter_resumo("meu-job/prod-sp", "homolog")

        assert resultado["lastBuild"]["number"] == 42

    def test_homolog_usa_lista_fixa_quando_ambiente_nao_tem_prod(self) -> None:
        """Sem "prod" no ambiente, tenta direto a lista fixa, em ordem."""
        lastvalue = json.dumps([{"lastBuild": _build_bruto()}])

        def _rpc(_method: str, params: dict) -> list:
            chave = params["search"]["key_"]
            if chave == "jenkins.job.mb.get[meu-job/hml]":
                return [{"lastvalue": lastvalue}]
            return []

        with patch(
            "apps.zabbix.services.jenkins.client.zabbix_rpc", side_effect=_rpc
        ):
            resultado = obter_resumo("meu-job/staging-x", "homolog")

        assert resultado["lastBuild"]["number"] == 42

    def test_homolog_fallback_por_prefixo_filtrado_por_ambiente(self) -> None:
        """No fallback por prefixo, só vale candidato com ambiente homolog."""
        lastvalue_prod = json.dumps(
            [
                {
                    "fullName": "meu-job/prod",
                    "lastBuild": _build_bruto(number=1, timestamp=5_000),
                }
            ]
        )
        lastvalue_homolog = json.dumps(
            [
                {
                    "fullName": "meu-job/homolog",
                    "lastBuild": _build_bruto(number=2, timestamp=1_000),
                }
            ]
        )
        candidatos_exatos = {
            f"jenkins.job.mb.get[meu-job/{c}]"
            for c in CANDIDATOS_HOMOLOG_FIXOS
        }

        def _rpc(_method: str, params: dict) -> list:
            chave = params["search"]["key_"]
            if chave in candidatos_exatos:
                return []
            if chave == "jenkins.job.mb.get[meu-job/":
                return [
                    {"lastvalue": lastvalue_prod},
                    {"lastvalue": lastvalue_homolog},
                ]
            return []

        with patch(
            "apps.zabbix.services.jenkins.client.zabbix_rpc", side_effect=_rpc
        ):
            resultado = obter_resumo("meu-job", "homolog")

        # mesmo o candidato "prod" tendo timestamp maior, só o "homolog" vale
        assert resultado["lastBuild"]["number"] == 2

    def test_homolog_sem_nenhum_candidato_retorna_vazio(self) -> None:
        """Sem nenhum candidato encontrado, retorna vazio."""
        with patch(
            "apps.zabbix.services.jenkins.client.zabbix_rpc",
            return_value=[],
        ):
            resultado = obter_resumo("meu-job", "homolog")

        assert resultado == {}
