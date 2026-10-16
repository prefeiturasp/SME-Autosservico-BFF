"""Testes da formatação de datas e durações do app azure."""

import pytest

from apps.azure.services.formatacao import formatar_data
from apps.azure.services.formatacao import formatar_rotulo_duracao
from apps.azure.services.formatacao import humanizar_duracao_horas
from apps.azure.services.formatacao import parsear_data_iso


class TestFormatarData:
    """Testes cobrindo formatar_data()."""

    def test_formata_timestamp_com_sufixo_z(self) -> None:
        """Um timestamp UTC com `Z` vira DD/MM/YYYY."""
        assert formatar_data("2026-03-09T13:45:12Z") == "09/03/2026"

    def test_aceita_sete_digitos_de_fracao(self) -> None:
        """A fração de segundo do Azure pode ter 7 dígitos."""
        assert formatar_data("2026-03-09T13:45:12.1234567Z") == "09/03/2026"

    @pytest.mark.parametrize("valor", ["", None, "data-invalida"])
    def test_retorna_none_quando_ausente_ou_invalido(
        self, valor: str | None
    ) -> None:
        """Valores ausentes ou não parseáveis viram None."""
        assert formatar_data(valor) is None


class TestParsearDataIso:
    """Testes cobrindo parsear_data_iso()."""

    def test_preserva_o_fuso(self) -> None:
        """O offset de fuso é mantido no datetime resultante."""
        momento = parsear_data_iso("2026-03-09T13:45:12Z")

        assert momento is not None
        assert momento.utcoffset() is not None
        assert momento.hour == 13

    def test_retorna_none_para_lixo(self) -> None:
        """Uma string não-ISO devolve None em vez de levantar."""
        assert parsear_data_iso("nao é data") is None


class TestHumanizarDuracaoHoras:
    """Testes cobrindo a escolha da unidade mais natural."""

    @pytest.mark.parametrize(
        ("horas", "esperado"),
        [
            (0.5, (30.0, "minutes")),
            (5, (5.0, "hours")),
            (48, (2.0, "days")),
            (24 * 60, (2.0, "months")),
            (24 * 400, (1.1, "years")),
        ],
    )
    def test_escolhe_a_unidade(
        self, horas: float, esperado: tuple[float, str]
    ) -> None:
        """Cada faixa de duração cai na unidade correspondente."""
        assert humanizar_duracao_horas(horas) == esperado


class TestFormatarRotuloDuracao:
    """Testes cobrindo o rótulo pt-br do tempo de atendimento."""

    @pytest.mark.parametrize(
        ("valor", "unidade", "esperado"),
        [
            (30.0, "minutes", "30min"),
            (5.0, "hours", "5h"),
            (2.0, "days", "2d"),
            (1.0, "months", "1 mês"),
            (2.0, "months", "2 meses"),
            (1.5, "months", "1,5 meses"),
            (1.0, "years", "1 ano"),
            (1.1, "years", "1,1 anos"),
        ],
    )
    def test_monta_o_rotulo(
        self, valor: float, unidade: str, esperado: str
    ) -> None:
        """Números inteiros perdem a casa decimal e o plural concorda."""
        assert formatar_rotulo_duracao(valor, unidade) == esperado
