"""
Fixtures specific to API unit tests.

This module provides fixtures for unit testing API controllers and services
without relying on the actual API endpoints. It focuses on testing the business
logic of API controllers in isolation from the HTTP layer.

Key components:
- Test data fixtures (workspaces, models, etc.)
- Mock fixtures for Socket.IO and other external dependencies
- Factory fixtures for creating controller-specific mocks

Unit testing approach for API components:
- Test controllers directly, bypassing FastAPI's request/response cycle
- Mock external services and dependencies
- Focus on business logic correctness
- Verify database interactions work as expected
"""

from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
import pytest
import pytest_asyncio

from mascope_backend.db.models import IonizationMechanism, Workspace


@pytest_asyncio.fixture(scope="session")
async def test_ionization_mechanisms(
    async_session_factory,
) -> list[IonizationMechanism]:
    """Create test ionization mechanism records in the unit test database.

    This fixture populates the database with ionization mechanisms that can be used
    by multiple unit tests.

    :param async_session_factory: Factory for creating database sessions
    :return: List of created ionization mechanism objects
    :rtype: list
    """
    async with async_session_factory() as session:
        ionization_mechanisms = [
            IonizationMechanism(
                ionization_mechanism_id="unit-test-1",
                ionization_mechanism_polarity="-",
                ionization_mechanism="-H-",
                reagent=None,
            ),
            IonizationMechanism(
                ionization_mechanism_id="unit-test-2",
                ionization_mechanism_polarity="-",
                ionization_mechanism="+Br-",
                reagent="CH2Br2",
            ),
            IonizationMechanism(
                ionization_mechanism_id="unit-test-3",
                ionization_mechanism_polarity="-",
                ionization_mechanism="+NO3-",
                reagent="HNO3",
            ),
            IonizationMechanism(
                ionization_mechanism_id="unit-test-4",
                ionization_mechanism_polarity="+",
                ionization_mechanism="+H+",
                reagent=None,
            ),
            IonizationMechanism(
                ionization_mechanism_id="unit-test-5",
                ionization_mechanism_polarity="+",
                ionization_mechanism="+(CH4N2O)H+",
                reagent="CH4N2O",
            ),
            IonizationMechanism(
                ionization_mechanism_id="unit-test-6",
                ionization_mechanism_polarity="+",
                ionization_mechanism="+",
                reagent=None,
            ),
            IonizationMechanism(
                ionization_mechanism_id="unit-test-7",
                ionization_mechanism_polarity="-",
                ionization_mechanism="-",
                reagent=None,
            ),
        ]

        for ionization_mechanism in ionization_mechanisms:
            session.add(ionization_mechanism)

        await session.commit()

        # Refresh to get all attributes
        for ionization_mechanism in ionization_mechanisms:
            await session.refresh(ionization_mechanism)

        return ionization_mechanisms


@pytest_asyncio.fixture(scope="session")
async def test_workspaces(async_session_factory):
    """Create test workspace records in the unit test database.

    This fixture populates the database with test workspaces that can be used
    by multiple unit tests. The workspaces are created once per test session
    for better performance.

    :param async_session_factory: Factory for creating database sessions
    :return: List of created workspace objects
    :rtype: list
    """
    async with async_session_factory() as session:
        workspaces = [
            Workspace(
                workspace_id="unit-test-1",
                workspace_name="Unit Test Workspace 1",
                workspace_description="This is a unit test workspace",
                workspace_utc_created=datetime.now(timezone.utc),
            ),
            Workspace(
                workspace_id="unit-test-2",
                workspace_name="Unit Test Workspace 2",
                workspace_description="This is another unit test workspace",
                workspace_utc_created=datetime.now(timezone.utc),
            ),
        ]

        for workspace in workspaces:
            session.add(workspace)

        await session.commit()

        # Refresh to get all attributes
        for workspace in workspaces:
            await session.refresh(workspace)

        return workspaces


@pytest.fixture
def mock_sio_factory():
    """Factory fixture for creating Socket.IO mocks for different controllers.

    This fixture returns a function that creates properly configured Socket.IO mocks
    for specific controllers. The factory approach allows each test module to create
    mocks that patch the correct import path for its specific controller.

    Benefits:
    1. Prevents real Socket.IO events during tests
    2. Allows verification of event emissions (event name, data, namespace, room)
    3. Records all calls to emit for assertion checking

    Verification Methods:
    - Verify event was called: mock_sio.emit.assert_called_once_with("event_name", namespace="/")
    - Verify specific event with room: mock_sio.emit.assert_any_call("event_name", room="room_id", namespace="/")
    - Check call count: assert mock_sio.emit.call_count == 2
    - Full history of all calls with their arguments: mock_sio.emit.call_args_list

    Usage examples:
    - In controller-specific conftest.py:
      @pytest.fixture
      def mock_sio_workspace(mock_sio_factory):
          return mock_sio_factory("mascope_backend.api.controllers.workspace.workspace_controller")

    - In tests:
      def test_something(mock_sio_workspace):
          # Use mock_sio_workspace for assertions

    :return: A function that creates and configures Socket.IO mocks
    :rtype: callable
    """

    def _make_mock_sio(module_path):
        """Create a Socket.IO mock for a specific module path.

        :param module_path: Full import path to the module using Socket.IO
        :type module_path: str
        :return: Configured AsyncMock for Socket.IO
        :rtype: MagicMock
        """
        # Create the patch for the specified module path
        mock = patch(f"{module_path}.sio").start()

        # Configure the mock with an AsyncMock for the emit method
        mock.emit = AsyncMock()

        # Return the configured mock
        return mock

    # Yield the factory function to the test
    yield _make_mock_sio

    # Clean up all patches after tests are done
    patch.stopall()
