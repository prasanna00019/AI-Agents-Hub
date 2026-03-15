import pytest
import importlib

def test_imports():
    """Test if critical packages can be imported."""
    packages = [
        "streamlit",
        "crewai",
        "langchain",
        "pydantic"
    ]
    for pkg in packages:
        try:
            importlib.import_module(pkg)
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import {pkg}: {e}")

def test_sample_addition():
    """A sample test for demonstration."""
    assert 1 + 1 == 2
