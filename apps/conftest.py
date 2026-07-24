"""Shared pytest fixtures for all apps."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    """Return a DRF APIClient instance for making test requests."""
    return APIClient()
