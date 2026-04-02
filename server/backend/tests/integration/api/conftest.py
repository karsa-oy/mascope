"""
API integration test fixtures.

This module provides fixtures for testing the full API request/response cycle
through FastAPI's TestClient. It focuses on realistic end-to-end testing of API
endpoints with proper authentication and database access.

Key components:
- Authentication fixtures (JWT token generation, authenticated clients)
- Role-based client fixtures (guest, editor, admin, owner)
- Test data fixtures for API requests
- Fundamental database fixtures (roles, users) used by authentication

Integration testing approach for API:
- Test API endpoints through the HTTP interface
- Verify role-based access control (RBAC) works correctly
- Test realistic request/response flows
- Verify proper error handling and status codes
- Test with realistic authentication

NOTE: Authentication and RBAC
These fixtures use a similar approach to Mascope app authentication system  by generating
valid JWT tokens and including them in cookies.
    1. The JWT token contains the user_id, which the application uses to determine permissions
    2. When a client makes a request, the application validates the JWT token
    3. The application then checks if the user's role has sufficient permissions for the operation
    4. If permissions are insufficient, the application returns 401 (Unauthorized) or 403 (Forbidden)
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.app.fast import fast
from mascope_backend.db import Role, User


@pytest_asyncio.fixture(scope="session")
async def roles(async_session_factory):
    """Create role fixtures for testing.

    This fixture has session scope because roles are fundamental data that doesn't change
    between tests. By creating roles once at the beginning of the test session:
        1. Improves test performance by avoiding repeated role creation
        2. Consistent role data is available to all tests

    This fixture uses async_session_factory directly (not the session fixture) because
    pytest doesn't allow session-scoped fixtures to depend on narrower-scoped fixtures.

    :param async_session_factory: Factory for creating sessions
    :type async_session_factory: async_sessionmaker
    :return: Dictionary of created role objects
    :rtype: dict[str, Role]
    """
    async with async_session_factory() as session:
        # Create roles from auth_settings.ROLE_ACCESS_LEVELS
        roles_config = {
            role_name: Role(role_id=access_level, role_name=role_name)
            for role_name, access_level in auth_settings.ROLE_ACCESS_LEVELS.items()
        }

        for role in roles_config.values():
            session.add(role)

        await session.commit()
        return roles_config


@pytest_asyncio.fixture(scope="session")
async def test_users(async_session_factory, roles):
    """Create test users with different roles (session-scoped).

    This fixture has session scope:
    1. Users are created only once for all tests, improving performance
    2. All tests have access to the same consistent set of test users
    3. Integration tests can rely on persistent user identities for authentication

    Like the roles fixture, this uses async_session_factory directly rather than
    the function-scoped session fixture to respect pytest's scope hierarchy.

    :param async_session_factory: Factory for creating sessions
    :type async_session_factory: async_sessionmaker
    :param roles: Dict of role objects
    :type roles: dict[str, Role]
    :return: Dictionary of user objects by role
    :rtype: dict[str, User]
    """
    # Create a session specifically for this fixture
    async with async_session_factory() as session:
        users = {
            "guest": User(
                email="guest@test.com",
                username="guest_user",
                hashed_password="123456",  # Not a real hash for testing
                is_active=True,
                is_verified=False,
                role_id=roles["guest"].role_id,
            ),
            "editor": User(
                email="editor@test.com",
                username="editor_user",
                hashed_password="123456",
                is_active=True,
                is_verified=False,
                role_id=roles["editor"].role_id,
            ),
            "admin": User(
                email="admin@test.com",
                username="admin_user",
                hashed_password="123456",
                is_active=True,
                is_verified=False,
                role_id=roles["admin"].role_id,
            ),
            "owner": User(
                email="owner@test.com",
                username="owner_user",
                hashed_password="123456",
                is_active=True,
                is_verified=False,
                is_superuser=True,
                role_id=roles["owner"].role_id,
            ),
        }

        for user in users.values():
            session.add(user)

        # commit instead of flush since this is session-level data
        await session.commit()

        # Refresh users to get their IDs
        for user in users.values():
            await session.refresh(user)

        return users
    # The session will be closed when the test session ends


@pytest.fixture
def create_jwt_auth_token():
    """
    Create a valid JWT token for testing protected api endpoints.

    This fixture returns a function that generates valid authentication tokens
    for testing role-based access control. The tokens generated match the
    format and claims expected by the application's authentication system.

    :return: A function that creates JWT tokens for specified users
    :rtype: Callable[[User], str]
    """

    def _create_token(user):
        # Create token payload matching your app's expectations
        payload = {
            "sub": str(user.id),  # Subject (user ID), used for authentication and RBAC
            "aud": auth_settings.JWT_AUDIENCE,  # Audience
            "exp": datetime.now(timezone.utc) + timedelta(days=1),  # Expiration
            "iat": datetime.now(timezone.utc),  # Issued at
        }

        # Generate the token using your app's settings
        token = jwt.encode(
            payload, auth_settings.JWT_SECRET_KEY, algorithm=auth_settings.JWT_ALGORITHM
        )

        return token

    return _create_token


@pytest.fixture
def guest_client(test_users, create_jwt_auth_token):
    """
    Create a TestClient authenticated as a guest user.

    This fixture creates a test client with guest-level permissions by:
        1. Generating a valid JWT token containing the guest user's user_id
        2. Adding this token to the client's cookies

    The client will use the test database because of the patch_db fixture.

    :param test_users: Dictionary of test user objects
    :type test_users: dict
    :param create_jwt_auth_token: Function to create JWT tokens
    :type create_jwt_auth_token: callable
    :return: TestClient with guest permissions
    :rtype: TestClient
    """
    # Generate a valid JWT token for the guest user
    token = create_jwt_auth_token(test_users["guest"])

    # Create a client with proper authentication
    client = TestClient(fast)

    # Set the auth cookie with the JWT token
    client.cookies.set(auth_settings.COOKIE_NAME, token)

    yield client


@pytest.fixture
def editor_client(test_users, create_jwt_auth_token):
    """
    Create a TestClient authenticated as an editor user.

    Editor users have all guest permissions plus additional capabilities
    specific to their role.

    :param test_users: Dictionary of test user objects
    :type test_users: dict
    :param create_jwt_auth_token: Function to create JWT tokens
    :type create_jwt_auth_token: callable
    :return: TestClient with editor permissions
    :rtype: TestClient
    """
    # Generate a valid JWT token for the editor user
    token = create_jwt_auth_token(test_users["editor"])

    # Create a client with proper authentication
    client = TestClient(fast)

    # Set the auth cookie with the JWT token
    client.cookies.set(auth_settings.COOKIE_NAME, token)

    yield client


@pytest.fixture
def admin_client(test_users, create_jwt_auth_token):
    """
    Create a TestClient authenticated as an admin user.

    Admin users have all guest and editor permissions plus additional
    capabilities specific to their role.

    :param test_users: Dictionary of test user objects
    :type test_users: dict
    :param create_jwt_auth_token: Function to create JWT tokens
    :type create_jwt_auth_token: callable
    :return: TestClient with admin permissions
    :rtype: TestClient
    """
    # Generate a valid JWT token for the admin user
    token = create_jwt_auth_token(test_users["admin"])

    # Create a client with proper authentication
    client = TestClient(fast)

    # Set the auth cookie with the JWT token
    client.cookies.set(auth_settings.COOKIE_NAME, token)

    yield client


@pytest.fixture
def owner_client(test_users, create_jwt_auth_token):
    """
    Create a TestClient authenticated as an owner user.

    Owner users have full access to all system capabilities.

    :param session: Database session for tests
    :type session: AsyncSession
    :param test_users: Dictionary of test user objects
    :type test_users: dict
    :param create_jwt_auth_token: Function to create JWT tokens
    :type create_jwt_auth_token: callable
    :return: TestClient with owner permissions
    :rtype: TestClient
    """
    # Generate a valid JWT token for the owner user
    token = create_jwt_auth_token(test_users["owner"])

    # Create a client with proper authentication
    client = TestClient(fast)

    # Set the auth cookie with the JWT token
    client.cookies.set(auth_settings.COOKIE_NAME, token)

    yield client


@pytest.fixture
def workspace_create_data():
    """Sample data for workspace creation requests.

    :return: Dictionary with workspace creation data
    :rtype: dict
    """
    return {
        "workspace_name": "New Test Workspace",
        "workspace_description": "Created during integration test",
        "workspace_type": "ANALYSIS",
    }


@pytest.fixture
def workspace_update_data():
    """Sample data for workspace update requests.

    This fixture provides a consistent dataset for testing workspace update endpoints.

    :return: Dictionary with workspace update data
    :rtype: dict
    """
    return {
        "workspace_name": "Updated Test Workspace",
        "workspace_description": "Updated during integration test",
    }


@pytest.fixture
def sample_batch_create_data():
    """Sample data for sample batch creation requests.

    This fixture provides a consistent dataset for testing sample batch creation endpoints.

    :return: Dictionary with sample batch creation data
    :rtype: dict
    """
    return {
        "sample_batch_name": "New Test Sample Batch",
        "sample_batch_description": "Sample batch for testing",
        "target_collection_ids": ["collection1", "collection2"],
    }
