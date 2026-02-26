"""
Doctest collection for pure utility functions.

This module automatically discovers and runs doctests from all modules
in the mascope_backend package that contain doctest examples.

To add doctests for a function, simply add Examples to its docstring:

    def my_function(x: int) -> int:
        '''Does something with x.

        Examples
        --------
        >>> my_function(5)
        10
        >>> my_function(0)
        0
        '''
        return x * 2
"""

import doctest
import sys

import pytest

# Package prefix to scan for doctests
PACKAGE_PREFIX = "mascope"


def _find_modules_with_doctests():
    """Find all imported modules with doctest examples."""
    modules_with_doctests = []

    for name, module in sys.modules.items():
        # Only check our package
        if not name.startswith(PACKAGE_PREFIX):
            continue
        # Skip None modules (can happen during import)
        if module is None:
            continue
        # Check if module has any doctests
        try:
            finder = doctest.DocTestFinder()
            tests = finder.find(module)
            if any(test.examples for test in tests):
                modules_with_doctests.append(name)
        except Exception:
            # Skip modules that can't be inspected
            continue

    return sorted(modules_with_doctests)


def pytest_generate_tests(metafunc):
    """Dynamically parametrize test with discovered doctest modules."""
    if "doctest_module_name" in metafunc.fixturenames:
        modules = _find_modules_with_doctests()
        metafunc.parametrize("doctest_module_name", modules)


@pytest.fixture
def doctest_module(doctest_module_name):
    """Return the module object for the given module name."""
    return sys.modules[doctest_module_name]


def test_doctests(doctest_module):
    """Run doctests for the discovered module.

    This test will fail if any doctest examples in the module fail.
    """
    results = doctest.testmod(
        doctest_module,
        optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
    )
    assert (
        results.failed == 0
    ), f"{results.failed} doctest(s) failed in {doctest_module.__name__}"
