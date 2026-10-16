"""Fixtures de pytest compartilhadas entre todos os apps."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    """Retorna uma instância de APIClient do DRF para requisições de teste."""
    return APIClient()
