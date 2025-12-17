"""
Test command for running and managing Mascope tests.

This module provides a CLI interface for running different types of tests
in the Mascope project. It supports different test components (backend, frontend)
and test modules (unit, integration, system).

Usage:
    mascope test run              # Run all backend tests
    mascope test run -m unit      # Run only unit tests
    mascope test run -n workspace_model # Run specific test by name
    mascope test list             # List available tests
"""

import os
from enum import Enum
import typer
from typing_extensions import Annotated

import mascope_cli.cmd.lib as lib
from mascope_cli.runtime import runtime

test_app = typer.Typer()


class TestComponent(str, Enum):
    """Components of the Mascope application that can be tested"""

    BACKEND = "backend"
    FRONTEND = "frontend"
    LIBRARIES = "libraries"


class TestModule(str, Enum):
    """Types of test modules available in the Mascope test suite"""

    UNIT = "unit"
    INTEGRATION = "integration"
    SYSTEM = "system"
    MASCOPE_SDK = "sdk"
    MASCOPE_TOOLS = "tools"
    ALL = "all"


@test_app.callback()
def main():
    """Run tests for Mascope components

    This command group provides tools for running and listing tests for
    different components of the Mascope application.
    """


@test_app.command()
def run(
    components: Annotated[
        list[TestComponent] | None,
        typer.Argument(
            help=f"Components to test [{', '.join([c.value for c in TestComponent])}]",
            show_default=f"{TestComponent.BACKEND.value}",
        ),
    ] = None,
    module: Annotated[
        TestModule | None,
        typer.Option(
            "--module",
            "-m",
            help=f"Test module type [{', '.join([m.value for m in TestModule])}]",
            case_sensitive=False,
        ),
    ] = None,
    test_name: Annotated[
        str | None,
        typer.Option(
            "--name",
            "-n",
            help="Run a specific test by name",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Run tests with verbose output",
        ),
    ] = False,
):
    """Run tests for specified Mascope components

    By default, this runs all backend tests. You can specify which components to test
    by providing them as arguments.

    Examples:\n
      mascope test run                      # Run all backend tests\n
      mascope test run -v                   # Run tests with verbose output\n
      mascope test run -m unit              # Run only unit tests\n
      mascope test run -n workspace_model   # Run a specific test by name\n
    """
    # Default to backend if no components specified
    if not components:
        if module in (TestModule.MASCOPE_SDK, TestModule.MASCOPE_TOOLS):
            components = [TestComponent.LIBRARIES]
        else:
            components = [TestComponent.BACKEND, TestComponent.LIBRARIES]

    # Set runtime environment for testing
    runtime.state.mode = "test"

    for component in components:
        if component == TestComponent.BACKEND:
            run_backend_tests(module, test_name, verbose)
        elif component == TestComponent.LIBRARIES:
            run_library_tests(module, test_name, verbose)
        elif component == TestComponent.FRONTEND:
            typer.echo("Frontend tests are not yet implemented")


def run_backend_tests(
    module: TestModule | None,
    test_name: str | None,
    verbose: bool,
):
    """Run backend tests with the specified options"""
    # Base command
    command = ["pytest"]

    # Path to tests - always use forward slashes for paths
    test_path = "server/backend/tests/"

    # Prevent sdk/tools from being treated as backend modules
    if module in (TestModule.MASCOPE_SDK, TestModule.MASCOPE_TOOLS):
        typer.echo("Module belongs to libraries; running library tests instead.")
        return run_library_tests(module, test_name, verbose)

    # Handle module selection using the enum value
    if module and module != TestModule.ALL:
        test_path = f"{test_path}{module.value}/"

    # If a specific test name is provided, search for it
    if test_name:
        # Check if it's a full path
        if "/" in test_name or "\\" in test_name:
            # Normalize path separators to forward slashes
            test_name = test_name.replace("\\", "/")
            test_path = f"{test_path}{test_name}"
            if not test_path.endswith(".py"):
                test_path += ".py"
        else:
            # Search for the test file
            found = False
            for root, _, files in os.walk(os.path.join("server", "backend", "tests")):
                for file in files:
                    if file.startswith("test_") and file.endswith(".py"):
                        # Extract test name without prefix and extension
                        name_match = file[5:-3]  # Strip "test_" and ".py"
                        if name_match == test_name:
                            # Found the test file - normalize to forward slashes
                            test_path = os.path.join(root, file).replace("\\", "/")
                            found = True
                            break
                if found:
                    break

            if not found:
                typer.echo(
                    f"Warning: Test '{test_name}' not found. Running specified module instead."
                )

    # Ensure all path separators are forward slashes for pytest
    test_path = test_path.replace("\\", "/")
    command.append(test_path)

    # Add options
    if verbose:
        command.append("-v")

    # Join command parts
    cmd_str = " ".join(command)

    # Run the command
    typer.echo(f"Running: {cmd_str}")
    lib.run(cmd_str)


def run_library_tests(
    module: TestModule | None,
    test_name: str | None,
    verbose: bool,
):
    """Run library tests with the specified options"""
    # Base command
    command = ["pytest"]

    # Path to tests - always use forward slashes for paths
    test_path = "libraries/"

    # Handle module selection using the enum value
    if module and module != TestModule.ALL:
        if module == TestModule.MASCOPE_SDK:
            test_path = f"{test_path}sdk/tests/"
        elif module == TestModule.MASCOPE_TOOLS:
            test_path = f"{test_path}tools/tests/"
        else:
            typer.echo(
                "Warning: Library tests are not separated into unit/integration/system modules. "
                "Running all library tests instead."
            )

    # If a specific test name is provided, search for it
    if test_name:
        # Check if it's a full path
        if "/" in test_name or "\\" in test_name:
            # Normalize path separators to forward slashes
            test_name = test_name.replace("\\", "/")
            test_path = f"{test_path}{test_name}"
            if not test_path.endswith(".py"):
                test_path += ".py"
        else:
            # Search for the test file
            found = False
            for root, _, files in os.walk("libraries"):
                for file in files:
                    if file.startswith("test_") and file.endswith(".py"):
                        # Extract test name without prefix and extension
                        name_match = file[5:-3]  # Strip "test_" and ".py"
                        if name_match == test_name:
                            # Found the test file - normalize to forward slashes
                            test_path = os.path.join(root, file).replace("\\", "/")
                            found = True
                            break
                if found:
                    break

            if not found:
                typer.echo(f"Warning: Test '{test_name}' not found. Exiting...")
                return

    # Ensure all path separators are forward slashes for pytest
    test_path = test_path.replace("\\", "/")
    command.append(test_path)

    # Add options
    if verbose:
        command.append("-v")

    # Join command parts
    cmd_str = " ".join(command)

    # Run the command
    typer.echo(f"Running: {cmd_str}")
    lib.run(cmd_str)


@test_app.command()
def show():
    """Show available test modules and test files

    This command scans the tests directory and shows all available test modules
    organized by their location. Each test is displayed with its name and path
    to make it easy to run specific tests with the 'run -n' command.
    """
    backend_tests_dir = "server/backend/tests"
    libraries_root_dir = "libraries"
    sdk_tests_dir = os.path.join(libraries_root_dir, "sdk", "tests")
    tools_tests_dir = os.path.join(libraries_root_dir, "tools", "tests")

    # ----- Backend tests -----
    if os.path.exists(backend_tests_dir):
        # Show module types using the enum
        for module in [m.value for m in TestModule if m != TestModule.ALL]:
            module_path = os.path.join(backend_tests_dir, module)

            if os.path.exists(module_path) and os.path.isdir(module_path):
                # Get count of test files in this module
                test_count = 0
                for root, _, files in os.walk(module_path):
                    test_count += sum(
                        1 for f in files if f.startswith("test_") and f.endswith(".py")
                    )

                typer.echo(f"\nbackend/{module}/ ({test_count} test files)")

                # Show subdirectories with their tests
                for item in sorted(os.listdir(module_path)):
                    item_path = os.path.join(module_path, item)

                    if os.path.isdir(item_path) and not item.startswith("__"):
                        # Count tests in this subdir
                        subdir_tests = []
                        for root, _, files in os.walk(item_path):
                            for file in sorted(
                                f
                                for f in files
                                if f.startswith("test_") and f.endswith(".py")
                            ):
                                # Get relative path from module directory
                                rel_path = os.path.relpath(
                                    os.path.join(root, file), module_path
                                )
                                rel_path = rel_path.replace("\\", "/")
                                test_name = file[5:-3]
                                subdir_tests.append((rel_path, test_name))

                        if subdir_tests:
                            typer.echo(f"  {item}/ ({len(subdir_tests)} test files)")
                            for rel_path, test_name in subdir_tests:
                                typer.echo(f"    - {test_name} → {rel_path}")

                # Check for test files directly in the module directory
                module_files = []
                for file in sorted(os.listdir(module_path)):
                    if file.startswith("test_") and file.endswith(".py"):
                        test_name = file[5:-3]
                        module_files.append((file, test_name))

                if module_files:
                    typer.echo(f"  (root) ({len(module_files)} test files)")
                    for file, test_name in module_files:
                        typer.echo(f"    - {test_name} → {file}")

        # Check for root test files
        root_tests = []
        for file in sorted(os.listdir(backend_tests_dir)):
            if file.startswith("test_") and file.endswith(".py"):
                test_name = file[5:-3]
                root_tests.append((file, test_name))

        if root_tests:
            typer.echo(f"\nbackend/root/ ({len(root_tests)} tests)")
            for file, test_name in root_tests:
                typer.echo(f"  - {test_name} → {file}")
    else:
        typer.echo(f"\nBackend tests directory not found at {backend_tests_dir}")

    # ----- Library tests (sdk/tools) -----
    def _show_library_section(title: str, base_dir: str):
        if not os.path.exists(base_dir):
            typer.echo(f"\n{title} tests directory not found at {base_dir}")
            return

        # Count all test_*.py files under this base_dir
        total = 0
        for root, _, files in os.walk(base_dir):
            total += sum(
                1 for f in files if f.startswith("test_") and f.endswith(".py")
            )

        typer.echo(f"\n{title}/ ({total} test files)")
        # Show subdirectories and files
        entries = []
        for root, _, files in os.walk(base_dir):
            for f in sorted(files):
                if f.startswith("test_") and f.endswith(".py"):
                    rel = os.path.relpath(os.path.join(root, f), base_dir).replace(
                        "\\", "/"
                    )
                    name = f[5:-3]
                    entries.append((rel, name))

        if entries:
            for rel, name in sorted(entries):
                typer.echo(f"  - {name} → {rel}")
        else:
            typer.echo("  (no tests found)")

    _show_library_section("libraries/sdk/tests", sdk_tests_dir)
    _show_library_section("libraries/tools/tests", tools_tests_dir)

    typer.echo("\nUsage examples:")
    typer.echo("  mascope test show                      # Show available tests")
    typer.echo("  mascope test run                       # Run all tests")
    typer.echo("  mascope test run -m unit               # Run only backend unit tests")
    typer.echo("  mascope test run libraries -m sdk      # Run SDK library tests")
    typer.echo("  mascope test run libraries -m tools    # Run Tools library tests")
    typer.echo("  mascope test run -n workspace_model    # Run specific test by name")
