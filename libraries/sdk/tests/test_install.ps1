# Create a virtual environment, install the package from TestPyPI and run tests
python -m venv temp
Set-Location temp
Scripts/activate
pip install --index-url https://test.pypi.org/simple/ mascope-sdk
python ..\tests\test_import.py

# Clean up
Scripts/deactivate
Set-Location ..
Remove-Item -Recurse -Force temp