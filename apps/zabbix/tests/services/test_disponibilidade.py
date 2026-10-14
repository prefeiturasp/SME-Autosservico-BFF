"""Testes do serviço de disponibilidade dos ambientes."""

from apps.zabbix.services.disponibilidade import listar_sistemas


def test_lista_inclui_producao_e_homologacao() -> None:
    """Sistema com HOM aparece com ``producao`` e ``homologacao``."""
    sistemas = {s["sistema"]: s for s in listar_sistemas()}

    assert sistemas["SigPAE"] == {
        "sistema": "SigPAE",
        "producao": "PRD - SIGPAE",
        "homologacao": "HOM - SIGPAE",
    }


def test_sistema_sem_homologacao_nao_tem_a_chave() -> None:
    """Sistema sem HOM não inclui a chave ``homologacao``."""
    sistemas = {s["sistema"]: s for s in listar_sistemas()}

    assert "homologacao" not in sistemas["Limpeza"]
    assert sistemas["Limpeza"]["producao"] == "PRD - Limpeza"
