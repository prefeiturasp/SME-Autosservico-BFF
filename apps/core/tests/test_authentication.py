"""Testes da autenticação por chave de API."""

import pytest
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.core.authentication import ApiKeyAuthentication

factory = APIRequestFactory()


class TestApiKeyAuthentication:
    """Testes cobrindo ApiKeyAuthentication.authenticate."""

    def test_returns_none_without_header(self) -> None:
        """Sem o header de chave, a autenticação é ignorada (retorna None)."""
        request = Request(factory.get("/"))

        assert ApiKeyAuthentication().authenticate(request) is None

    def test_raises_when_key_is_invalid(self, settings) -> None:
        """Uma chave incorreta levanta AuthenticationFailed."""
        settings.API_KEY = "chave-correta"
        request = Request(factory.get("/", HTTP_X_API_KEY="chave-errada"))

        with pytest.raises(AuthenticationFailed):
            ApiKeyAuthentication().authenticate(request)

    def test_authenticates_with_valid_key(self, settings) -> None:
        """Uma chave correta autentica a requisição."""
        settings.API_KEY = "chave-correta"
        request = Request(factory.get("/", HTTP_X_API_KEY="chave-correta"))

        result = ApiKeyAuthentication().authenticate(request)

        assert result is not None
        user, auth = result
        assert auth is None
        assert user.is_authenticated
