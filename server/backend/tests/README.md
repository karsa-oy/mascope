# Mascope Test Framework

## Test Categories 📚

### **Unit tests**

Tests that verify individual components in isolation with external dependencies mocked.

- **API unit tests**: Validate Pydantic models, service/controllers without actual HTTP requests
  - Example: Testing the `workspace_controller` functions directly to verify business logic with mocked socketio service
  - Focus: Schema validation, service logic, error handling
- **DB unit tests**: Verify database models, queries, and relationships in isolation
  - Example: Testing that `Workspace` model properties and relationships to `SampleBatch` work correctly
  - Focus: Model validation, relationships, cascading behaviors
- **Libraries unit tests**: Test that core library functions work correctly in isolation
  - Example: Testing signal processing algorithms independently with controlled inputs
  - Focus: Function behavior, edge cases, error handling

### **Integration tests**

Tests that verify interactions between multiple components but not the entire system.

- **API integration tests**: Test complete HTTP request/response cycle with real dependencies
  - Example: Testing CRUD operations on the `/api/workspaces` endpoint with authentication, verifying role-based access control (RBAC) for different user roles
  - Focus: HTTP status codes, response formats, role-based access control (RBAC)
- **DB integration tests**: Verify multi-model interactions and complex query operations
  - Example: Testing relationships between tables and model, deep cascade-delete tests, database integrity tests, test backup/restore functionality
  - Focus: Data persistence, complex queries, transaction integrity
- **Libraries integration tests**: Test interactions between multiple library components
  - Example: Testing how peak detection interacts with signal processing

### **System tests**

Tests that verify complete application workflows from end to end.

- **Pipelines**: Test data processing and transformation processes
  - Example: Testing a signal processing pipeline from raw data to peak detection
  - Focus: Data integrity through transformation stages, algorithm accuracy
- **Workflows**: Test complete business processes involving multiple API endpoints
  - Example: Testing the complete sample analysis workflow (creation, processing)
  - Example: Creating a workspace, adding sample batches, importing data.
  - Example: Verifying data export and report generation processes
  - Focus: End-to-end user scenarios, business logic correctness
- **Regression**: Ensure previously fixed bugs don't reappear
  - Example: Testing specific scenarios that previously caused failures
  - Focus: Bug-specific test cases, backward compatibility
- **Security**: Test authentication, authorization, and security measures
  - Example: Testing token validation and expiry
  - Focus: Authentication flows, authorization rules, security vulnerabilities
- **Performance**: Measure system response times, resource utilization, system stability.
  - **Load tests**: Verify behavior under expected usage conditions
    - Example: Testing with expected number of concurrent users
  - **Stress tests**: Verify behavior under extreme conditions
    - Example: Testing with excessive concurrent requests

## Directory Structure Overview 📂

```

server/backend/tests/
├── conftest.py                    # Core pytest fixtures, db engine factory
├── pytest.ini                     # Test configuration and settings
├── README.md                      # Documentation for the test framework
├── unit/                          # Individual components in isolation
│   ├── conftest.py                # Unit tests database engine and session fixtures
│   ├── api/                       # API component unit tests
│   │   ├── conftest.py            # API-specific mocks (socketio, dependencies)
│   │   ├── workspace/             # Workspace-specific unit tests
│   │   │   ├── conftest.py        # Workspace test data fixtures
│   │   │   ├── test_workspace_schema.py  # Test Pydantic model validation, constraints
│   │   │   └── test_workspace_service.py # Test controller logic
│   │   ├── other resources....
│   ├── db/                        # Database component unit tests
│   │   ├── conftest.py            # DB-specific fixtures for isolated model testing
│   │   └── models/                # SQLAlchemy model tests
│   │       ├── conftest.py        # Test data fixtures for database model tests.
│   │       ├── test_workspace_model.py   # Test workspace model
│   ├── libraries/                 # Library components unit tests
│       ├── conftest.py            # Fixtures for library testing
├── integration/                   # Tests for component interactions
│   ├── conftest.py                # Integration test database/session setup
│   ├── api/                       # API integration tests by resource
│   │   ├── conftest.py            # Authenticated TestClient fixtures for RBAC
│   │   └── workspace/             # Workspace API integration tests
│   │   │   └── test_workspace_crud.py  # Workspace CRUD lifecycle tests
│   │   ├── other resources....
│   ├── db/                        # Database integration tests
│   │   ├── conftest.py            # Multi-model database fixtures
│   │   └── test_cascade_deletes.py     # Verify model relationship behaviors
│   ├── libraries/                 # Library interaction tests
│       ├── conftest.py            # Fixtures for library component interactions
├── system/                        # End-to-end workflow tests
│   ├── conftest.py                # Setup for system testing
│   ├── pipelines/                 # Data processing pipeline tests
│   │   ├── conftest.py            # Test dataset fixtures, pipeline mocks
│   │   ├── test_signal_processing.py  # Signal processing pipeline
│   │   └── test_peak_detection.py     # Peak detection pipeline
│   ├── workflows/                 # Business process workflow tests
│   │   ├── conftest.py            # Workflow execution fixtures
│   │   ├── test_sample_processing.py   # Sample creation and analysis workflow
│   │   └── test_workspace_lifecycle.py # Complete workspace/batch/sample lifecycle
│   ├── regression/                # Tests for previously fixed bugs
│   │   ├── conftest.py            # Bug reproduction fixtures
│   │   └── test_fixed_bugs.py     # Tests for specific historical bug fixes
│   ├── security/                  # Security-focused testing
│   │   ├── conftest.py            # Security test fixtures
│   │   └── test_authentication.py # JWT token validation, expiry, refresh tests
│   └── performance/               # System performance tests
│       ├── conftest.py            # Performance test configuration
│       ├── load/                  # Expected load testing
│       │   └── test_concurrent_users.py  # Test with normal expected users
│       └── stress/                # Extreme conditions testing
│           └── test_high_concurrency.py  # Test with excessive concurrent requests
└── old/                           # Tests preserved for future refactoring
    ├── test_signal_processing_pipeline.py
    ├── test_peak_fitting.py
    └── test_target_ion_compute.py

```

## Testing Tools Glossary 📖

### Pytest concepts

- **Fixtures**: Reusable test resources defined with `@pytest.fixture`
  - Automatically discovered in `conftest.py` files
  - Available to all tests in the same directory and subdirectories by name (can be redefined, no need to import)
  - More specific conftest fixtures override those with the same name from parent directories
- **Fixture scopes**: Control lifecycle of fixture resources
  - `function` (default): Created for each test
  - `class`, `module`, `session`: Created once per class/module/session
  - **⚠️ CRITICAL RULE: A wider-scoped fixture cannot depend on a narrower-scoped fixture.** The fixture dependency chain must always flow from narrower scope to wider scope: `function → class → module → session`, not the other way around
- **Conftest hierarchy**: Determines fixture discovery and priority
  - `conftest.py` files searched from test file up to root
  - More specific conftest takes precedence for same-named fixtures
  - Each directory level can have its own `conftest.py`
- **pytest-asyncio**: Support for async tests and fixtures
  - Async tests use `@pytest.mark.asyncio` decorator
  - Async fixtures use `@pytest_asyncio.fixture`
  - Explicitly required due to configuration in pytest.ini `asyncio_mode = strict`

### Test tools

- **TestClient**: FastAPI testing utility
  - Creates a test version of application without starting a server
  - Each TestClient instance is a separate application instance with its own state
  - Simulates HTTP requests: `client.get("/api/workspaces")`
  - TestClient is synchronous
- **Mocking**: Replacing real objects with test doubles
  - `AsyncMock`: For mocking async functions
  - `patch`: For temporarily replacing objects during tests
  - Use for isolating the code under test from external dependencies

### Database testing

- **In-memory SQLite**: Isolated test databases
  - Uses `"sqlite+aiosqlite:///:memory:"` connection string
  - Each test category gets its own isolated database
  - Database patching redirects app connections to test database
  - Automatically discarded after test completion

### Configuration file pytest.ini

- **pytest.ini**: Central pytest configuration file
  - **Test discovery settings**:
    - `testpaths = tests`: Where to look for tests
    - `python_files = test_*.py`: Files considered as tests
    - `norecursedirs = tests/old`: Directories to exclude
  - **Asyncio settings**:
    - `asyncio_mode = strict`: Requires marking async tests explicitly
    - `asyncio_default_fixture_loop_scope = session`: Single event loop for all tests

## Core Implementation Patterns 🔧

### Database isolation architecture

- **Factory-based database creation**: The root `conftest.py` provides a session-scoped `async_engine_factory` that creates isolated in-memory SQLite databases for different test categories, keeping unit and integration tests completely separate.
- **Category-specific engines**: Unit and integration tests each create their own isolated database using the factory. The `async_engine` fixture specified in each test category level conftest files (e.g., "unit_tests", "integration_tests") to maintain isolation. System tests will likely use real test datasets instead of in-memory databases.
- **Automatic database patching**: The `patch_db` fixture with `autouse=True` redirects all application database access to the test database, allowing application code to interact with test data without modification.

### Authentication testing infrastructure

- **Role hierarchy persistence**: For API integration tests, session-scoped fixtures create persistent user and role records that mirror the application's authorization system. The `roles` and `test_users` fixtures establish this foundational data once per test session.
- **JWT token infrastructure**: Specifically for API integration tests, the `create_jwt_auth_token` fixture provides a function that generates valid JWT tokens matching the application's security specifications, with proper payload structure and signing.
- **Role-based client fixtures**: For testing protected routes, pre-configured TestClient instances (`guest_client`, `editor_client`, `admin_client`, `owner_client`) provide realistic authentication context for verifying role-based access control (RBAC).
- **Complete auth simulation**: Rather than mocking authentication logic, the API integration tests emulate the entire authentication flow, including token generation, cookie-based token storage, and server-side validation.

### Mock implementation strategies

- **Factory pattern for mocks**: The `mock_sio_factory` creates specialized Socket.IO mocks that patch the exact module path where services import Socket.IO. Each controller needs to be patched at its specific import path, not at a global level.
- **Component-specific mocks**: Specialized fixtures like `mock_sio_workspace` target specific modules with the correct import paths, preventing side effects in other components.
- **Verification support**: Mocks include pre-configured AsyncMock instances for async methods like Socket.IO's `emit`, allowing tests to verify event emissions with assertions like `mock_sio.emit.assert_called_once_with()`.

### Test data management

- **Proximity vs. DRY balance**: Test fixtures follow two complementary approaches:
  - **Proximity principle**: Keep fixtures close to their tests in component-specific conftest files
  - **DRY principle**: Share common fixtures at appropriate levels to avoid duplication
- **Layered test data**: Component-specific fixtures provide standardized test data (e.g., `workspace_create_data`) for consistent testing scenarios across multiple tests.
- **Model factories**: Fixtures like `workspace_create_model` create properly structured Pydantic models for validation and schema testing.
- **Isolation strategy**: Session-scoped fixtures provide persistent reference data for efficiency, while function-scoped fixtures offer test-specific isolation.

## Running Tests ▶️

The test framework can be executed using either pytest directly or the specialized Mascope CLI testing commands.

### Using pytest directly 🐍

Run tests from the repository root:

```bash
# Run all tests
pytest server/backend/tests/
# Run a specific test file
pytest server/backend/tests/unit/api/workspace/test_workspace_schema.py
```

Common pytest options:

- `v`: Verbose output showing each test name
- `s`: Show print statements during test execution
- `durations=10`: Show execution time for the 10 slowest tests
- `k "workspace"`: Run only tests with "workspace" in their name

### Using Mascope CLI 💻

The Mascope CLI provides a specialized interface for running and discovering tests:

### Discovering available tests 🔍

List all available test modules and files:

```bash
mascope test list
```

This command displays tests organized by category (unit, integration, system) with their specific names, making it easy to identify which tests to run.

### Running tests ▶️

Run all backend tests:

```bash
mascope test run
```

Run specific test categories:

```bash
# Run only unit tests
mascope test run -m unit
# Run only integration tests
mascope test run -m integration
```

Run a specific test by name:

```bash
# Run the workspace_model test
mascope test run -n workspace_model
# Run with verbose output
mascope test run -n workspace_crud -v
```

### CI/CD integration 🚀

Tests run automatically on GitHub Actions when creating or updating pull requests to the develop branch. The workflow is defined in `.github/workflows/tests.yaml` and:

- Runs on each PR to develop branch (opened, synchronized, or reopened)
- Executes all tests with verbose output (`v` flag)

### Recommended testing workflow 📋

1. **Explore available tests** using `mascope test list` to understand what tests exist
2. **Run focused tests** during development with `mascope test run -n test_name` to verify specific functionality
3. **Run category tests** before committing with `mascope test run -m unit` or `mascope test run -m integration`
4. **Run the full test suite** before major PRs with `mascope test run`
5. **Review GitHub Actions results** and logs after creating a PR
