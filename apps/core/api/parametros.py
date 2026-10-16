"""Leitura e validação de parâmetros de query string das views."""

from rest_framework.exceptions import ValidationError
from rest_framework.request import Request


def param_int(request: Request, nome: str) -> int:
    """Lê e valida um parâmetro inteiro obrigatório da query string."""
    valor = request.query_params.get(nome)
    if valor is None:
        raise ValidationError({nome: "Parâmetro obrigatório."})
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ValidationError({nome: "Deve ser um inteiro."}) from exc
