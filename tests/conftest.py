"""Pytest configuration and fixtures for integration tests.

Provides FastAPI TestClient fixture for in-process API testing
without requiring a running server.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture for integration tests.
    
    Uses module scope to reuse client across tests for performance.
    TestClient automatically handles lifespan context manager,
    initializing the global state_manager before tests run.
    """
    with TestClient(app) as test_client:
        yield test_client
