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
- **Doctests**: Test isolated functions with inline examples
  - Example: Test that regular expression used for ion formula parsing returns correct result
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
├── conftest.py                    # Core pytest fixtures, PostgreSQL engine factory
├── pytest.ini                     # Test configuration and settings
├── test_utils.py                  # Shared test utilities (gen_test_id)
├── README.md                      # Documentation for the test framework
├── unit/                          # Individual components in isolation
│   ├── conftest.py                # Unit test database engine and session fixtures
│   ├── api/                       # API component unit tests
│   │   ├── conftest.py            # API-specific mocks (socketio, dependencies), session-scoped test data
│   │   ├── workspace/             # Workspace-specific unit tests
│   │   │   ├── conftest.py        # Workspace test data fixtures
│   │   │   ├── test_workspace_schema.py  # Test Pydantic model validation, constraints
│   │   │   └── test_workspace_service.py # Test controller logic
│   │   ├── other resources....
│   ├── db/                        # Database component unit tests
│   │   ├── conftest.py            # Function-scoped session fixture for isolated model testing
│   │   └── models/                # SQLAlchemy model tests
│   │       ├── conftest.py        # Test data fixtures for database model tests
│   │       ├── test_workspace_model.py   # Test workspace model
│   ├── libraries/                 # Library components unit tests
│       ├── conftest.py            # Fixtures for library testing
├── integration/                   # Tests for component interactions
│   ├── conftest.py                # Integration test database/session setup
│   ├── api/                       # API integration tests by resource
│   │   ├── conftest.py            # AsyncClient fixtures for RBAC, roles, users
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
│   │   ├── workflow_utils.py      # Workflow-specific test helpers
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

libraries/
├── sdk/tests
    ├── conftest.py                # Fixtures for Mascope SDK tests
    └── test_import.py             # Tests SDK import functions
├── tools/tests
    ├── conftest.py                # Fixtures for Mascope Tools library tests
    └── test_calibration.py        # Tests calibration module functions
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

- **AsyncClient**: Primary HTTP test client for API integration tests
  - Uses `httpx.AsyncClient` with `ASGITransport(app=fast)` and `base_url="http://test"`
  - Runs in the same event loop as the test session — required for asyncpg compatibility (see [FastAPI Async Tests](https://fastapi.tiangolo.com/advanced/async-tests/#example))
  - Simulates HTTP requests: `await client.get("/api/workspaces")`
  - All API integration tests are `async def` with `@pytest.mark.asyncio`
- **TestClient**: FastAPI's synchronous test client — not used in integration tests
  - Would cause `InterfaceError: cannot perform operation: another operation is in progress`
  - because it runs the ASGI app in a separate thread with its own event loop, incompatible
  - with asyncpg connections that are bound to the session event loop
- **Mocking**: Replacing real objects with test doubles
  - `AsyncMock`: For mocking async functions
  - `patch`: For temporarily replacing objects during tests
  - Use for isolating the code under test from external dependencies

### Database testing

- **Isolated PostgreSQL databases**: One ephemeral database per test category
  - Created at session start: `mascope_test_unit_tests`, `mascope_test_integration_tests`
  - Dropped at session end; schema is recreated fresh on every run via `Base.metadata.create_all`
  - Requires the dev PostgreSQL container to be running locally (`mascope dev up`)
  - In CI, a `postgres:16-alpine` service container is started automatically by GitHub Actions
- **Database patching**: `patch_db` fixture with `autouse=True` redirects `ASYNC_SESSION_MAKER`
  - Affects both `async_session()` (controllers/services) and `get_async_session()` (FastAPI DI)
  - Ensures all application code operates on the isolated test database for the duration of the session
- **Event loop requirements**: asyncpg socket transports are bound to the event loop they were
  created in and cannot be transferred. `asyncio_default_fixture_loop_scope = session` and
  `asyncio_default_test_loop_scope = session` in `pytest.ini` ensure all fixtures and tests
  share one loop, preventing `InterfaceError: cannot perform operation: another operation is in progress`

### Test ID generation

- **`gen_test_id(size=16)`** in `tests/test_utils.py` generates random IDs using `nanoid`
  - Default size matches the `VARCHAR(16)` primary key constraint enforced by PostgreSQL
  - Use for all model fixtures that require a primary key: `workspace_id=gen_test_id()`
  - Pass `size` explicitly when a column has a different length constraint
  - Stable module-level constants are used only where parametrized tests must reference IDs by value

### Configuration file pytest.ini

- **pytest.ini**: Central pytest configuration file
  - **Test discovery settings**:
    - `testpaths = tests`: Where to look for tests
    - `python_files = test_*.py`: Files considered as tests
    - `norecursedirs = tests/old`: Directories to exclude
  - **Asyncio settings**:
    - `asyncio_mode = strict`: Requires marking async tests explicitly with `@pytest.mark.asyncio`
    - `asyncio_default_fixture_loop_scope = session`: Single event loop for all async fixtures
    - `asyncio_default_test_loop_scope = session`: Test functions share the session event loop —
      required so that asyncpg connections created in session-scoped fixtures are accessible
      from test functions without crossing event loop boundaries

## Core Implementation Patterns 🔧

### Database isolation architecture

- **Async factory-based database creation**: The root `conftest.py` provides a session-scoped
  `async_engine_factory` — an async fixture that yields an async callable. Each call creates an
  ephemeral `mascope_test_{category}` PostgreSQL database (drop if exists → create → `create_all`),
  tracked for teardown at session end. The factory must be awaited from an async session-scoped
  fixture — using `asyncio.run()` would create a separate event loop, leaving asyncpg transports
  bound to a dead loop and causing `InterfaceError` on first use.
- **Category-specific engines**: Unit and integration tests each call the factory with their
  category name (`"unit_tests"`, `"integration_tests"`) to get a fully isolated engine and database.
  System tests use real datasets and are not wired to the factory.
- **Automatic database patching**: The `patch_db` fixture with `autouse=True` replaces
  `db_module.ASYNC_SESSION_MAKER` for the duration of the session, redirecting all application
  database access to the test database without requiring any changes to test functions.

### Authentication testing infrastructure

- **Role hierarchy persistence**: For API integration tests, session-scoped fixtures create
  persistent `Role` and `User` records that mirror the application's authorization system.
  The `roles` and `test_users` fixtures establish this foundational data once per session.
- **JWT token infrastructure**: The `create_jwt_auth_token` fixture provides a factory function
  that generates valid JWT tokens matching the application's security specifications, with proper
  payload structure (`sub`, `aud`, `exp`, `iat`) and signing via `auth_settings`.
- **Role-based client fixtures**: Pre-configured `AsyncClient` instances (`guest_client`,
  `editor_client`, `admin_client`, `owner_client`) inject auth cookies at construction time via
  the `cookies=` parameter, providing realistic RBAC context for each test.
- **Complete auth simulation**: Tests emulate the full authentication flow — token generation,
  cookie injection, server-side JWT validation, and role resolution — rather than mocking it.

### Mock implementation strategies

- **Factory pattern for mocks**: The `mock_emit_record_factory` creates specialized mocks for
  `emit_record_created`, `emit_record_updated`, and `emit_record_deleted`. The factory patches
  the exact module path where controllers import these functions — each controller must be patched
  at its specific import path, not globally.
- **Component-specific mocks**: Fixtures like `mock_emit_workspace` target specific module paths,
  preventing side effects in other components. The mock returns a `MagicMock` container with three
  `AsyncMock` attributes (`created`, `updated`, `deleted`) for verifying each emission type.
- **Verification support**:
  - `mock_emit_workspace.created.assert_called_once()` — verify creation event
  - `mock_emit_workspace.updated.assert_called_with(record_type="workspace", ...)` — verify update
  - `mock_emit_workspace.deleted.call_count == 2` — verify delete count
  - `call_args.kwargs["record_type"]` — verify specific event parameters

### Test data management

- **Proximity vs. DRY balance**: Test fixtures follow two complementary approaches:
  - **Proximity principle**: Keep fixtures close to their tests in component-specific conftest files
  - **DRY principle**: Share common fixtures at appropriate levels to avoid duplication
- **ID generation**: Use `gen_test_id()` from `test_utils.py` for all model primary keys.
  PostgreSQL enforces `VARCHAR(16)` length and foreign key constraints that SQLite silently ignored.
- **Layered test data**: Component-specific fixtures provide standardized test data (e.g.,
  `workspace_create_data`) for consistent testing scenarios across multiple tests.
- **Isolation strategy**: Session-scoped fixtures provide persistent reference data (roles, users,
  ionization mechanisms) for efficiency. Function-scoped fixtures (`session` in `unit/db/conftest.py`)
  provide per-test isolation — data flushed but not committed is rolled back on session close.

## Running Tests ▶️

### Prerequisites

Local tests require the dev PostgreSQL container to be running:

```bash
mascope dev up
```

This starts the `mascope_dev_postgres` container at `localhost:5432`. The test factory creates
and drops `mascope_test_unit_tests` and `mascope_test_integration_tests` databases against it.
Password is read from `.runtime/secrets/postgres_password.txt` via `MASCOPE_PATH`.

### Using pytest directly 🐍

Run tests from the repository root:

```bash
# Run all tests
pytest server/backend/tests/

# Run a specific test file
pytest server/backend/tests/unit/api/workspace/test_workspace_schema.py
```

Common pytest options:

- `-v`: Verbose output showing each test name
- `-s`: Show print statements during test execution
- `--durations=10`: Show execution time for the 10 slowest tests
- `-k "workspace"`: Run only tests with "workspace" in their name

### Using Mascope CLI 💻

The Mascope CLI provides a specialized interface for running and discovering tests.

#### Discovering available tests 🔍

```bash
mascope test list
```

This command displays tests organized by category (unit, integration, system) with their specific names.

#### Running tests ▶️

```bash
# Run all backend tests
mascope test run

# Run only unit tests
mascope test run -m unit

# Run only integration tests
mascope test run -m integration

# Run a specific test by name
mascope test run -n workspace_model

# Run with verbose output
mascope test run -n workspace_crud -v

# Run all SDK library tests
mascope test run libraries -m sdk

# Run all Tools library tests
mascope test run libraries -m tools
```

### CI/CD integration 🚀

Tests run automatically on GitHub Actions on each PR to the `develop` branch. The workflow
(`.github/workflows/tests.yaml`) starts a `postgres:16-alpine` service container before the
test job runs, with credentials matching `POSTGRES_TEST_PASSWORD` in the test step env block.
The container is destroyed when the job completes.

### Recommended testing workflow 📋

1. **Start dependencies** with `mascope dev up` before running any tests locally
2. **Explore available tests** using `mascope test list` to understand what tests exist
3. **Run focused tests** during development with `mascope test run -n test_name` to verify specific functionality
4. **Run category tests** before committing with `mascope test run -m unit` or `mascope test run -m integration`
5. **Run the full test suite** before major PRs with `mascope test run`
6. **Review GitHub Actions results** and logs after creating a PR
