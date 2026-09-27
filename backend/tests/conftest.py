"""
Shared pytest configuration and global fixtures for backend test suite.
Automatically configures authentication dependency overrides for tests.
"""

import pytest
from backend.main import app
from backend.auth import get_current_user

DEFAULT_TEST_USER_ID = "test-tenant-user-uuid"


@pytest.fixture(autouse=True)
def default_auth_override():
    """
    Automatically injects default authenticated test tenant ID into get_current_user
    for all integration and API test suites.
    """
    app.dependency_overrides[get_current_user] = lambda: DEFAULT_TEST_USER_ID
    yield
    app.dependency_overrides.pop(get_current_user, None)
