"""Testes da leitura somente-leitura de bancos PostgreSQL externos."""

from unittest.mock import MagicMock
from unittest.mock import patch

from psycopg.rows import dict_row

from apps.core.postgres_leitura import executar_consulta_leitura


def _mock_conexao(mock_connect: MagicMock, linhas: list[dict]) -> MagicMock:
    """Configura ``psycopg.connect`` mockado como context manager aninhado.

    Args:
        mock_connect: O mock de ``psycopg.connect``.
        linhas: Linhas que ``cursor.fetchall()`` deve retornar.

    Returns:
        O mock do cursor, para inspecionar as chamadas feitas nele.
    """
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchall.return_value = linhas

    mock_conexao = MagicMock()
    mock_conexao.__enter__ = MagicMock(return_value=mock_conexao)
    mock_conexao.__exit__ = MagicMock(return_value=False)
    mock_conexao.cursor.return_value = mock_cursor

    mock_connect.return_value = mock_conexao
    return mock_cursor


class TestExecutarConsultaLeitura:
    """Testes cobrindo executar_consulta_leitura()."""

    def test_conecta_e_executa_a_query_sem_params(self) -> None:
        """Sem params, a query é executada com uma tupla vazia."""
        with patch("psycopg.connect") as mock_connect:
            mock_cursor = _mock_conexao(mock_connect, [{"total": 27583}])

            resultado = executar_consulta_leitura(
                "postgresql://usuario:senha@host/banco",
                "SELECT total FROM acessos",
            )

        assert resultado == [{"total": 27583}]
        mock_connect.assert_called_once_with(
            "postgresql://usuario:senha@host/banco", row_factory=dict_row
        )
        mock_cursor.execute.assert_called_once_with(
            "SELECT total FROM acessos", ()
        )

    def test_executa_a_query_com_params(self) -> None:
        """Params posicionais são repassados para o cursor."""
        with patch("psycopg.connect") as mock_connect:
            mock_cursor = _mock_conexao(mock_connect, [])

            executar_consulta_leitura(
                "postgresql://usuario:senha@host/banco",
                "SELECT * FROM acessos WHERE ano = %s",
                (2026,),
            )

        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM acessos WHERE ano = %s", (2026,)
        )

    def test_retorna_lista_vazia_sem_linhas(self) -> None:
        """Uma consulta sem resultados retorna uma lista vazia."""
        with patch("psycopg.connect") as mock_connect:
            _mock_conexao(mock_connect, [])

            resultado = executar_consulta_leitura(
                "postgresql://usuario:senha@host/banco", "SELECT 1"
            )

        assert resultado == []
