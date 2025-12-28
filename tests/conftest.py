import pytest


@pytest.fixture
def tmpdir(tmp_path):
    """Alias tmpdir to tmp_path for compatibility."""
    return tmp_path
