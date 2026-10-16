"""Autenticação por chave de API, padrão SME para microsserviços."""

import hmac
from dataclasses import dataclass

from django.conf import settings
from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.request import Request


@dataclass(frozen=True)
class ServicoAutenticado:
    """Representa o serviço chamador autenticado via chave de API.

    Este BFF não possui banco de dados nem modelo de usuário (ver
    arquitetura C3 — serviço stateless), por isso não usa
    ``django.contrib.auth.models.User``/``AnonymousUser``: esta classe
    expõe apenas o contrato mínimo exigido pelas permissions do DRF
    (``is_authenticated``).
    """

    is_authenticated: bool = True
    is_anonymous: bool = False


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """Autentica requisições via chave de API enviada em um header HTTP.

    O nome do header e a chave esperada são configurados através das
    variáveis de ambiente ``API_KEY_HEADER`` e ``API_KEY``.
    """

    def authenticate(
        self, request: Request
    ) -> tuple[ServicoAutenticado, None] | None:
        """Valida a chave de API enviada na requisição.

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Uma tupla ``(ServicoAutenticado(), None)`` quando a chave é
            válida, ou ``None`` quando nenhum header de chave foi enviado
            (deixando a decisão para outras classes de
            autenticação/permissão).

        Raises:
            AuthenticationFailed: Quando o header foi enviado, mas a chave
                é inválida.
        """
        api_key = request.headers.get(settings.API_KEY_HEADER)
        if not api_key:
            return None
        if not settings.API_KEY or not hmac.compare_digest(
            api_key, settings.API_KEY
        ):
            raise exceptions.AuthenticationFailed("Chave de API inválida.")
        return (ServicoAutenticado(), None)

    def authenticate_header(self, request: Request) -> str:
        """Nome do header esperado, usado pelo DRF para a resposta 401.

        Sem isto, o DRF rebaixa automaticamente respostas de
        credenciais ausentes/inválidas de 401 para 403 (a especificação
        HTTP exige um header ``WWW-Authenticate`` em respostas 401).

        Args:
            request: Requisição HTTP recebida.

        Returns:
            Nome do header de API Key configurado via ``API_KEY_HEADER``.
        """
        return str(settings.API_KEY_HEADER)
