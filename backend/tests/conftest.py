import pytest

from app.data.loader import load_store
from app.deps import DATA_DIR


@pytest.fixture(scope="session")
def full_store():
    """The real dataset (cached on disk by the loader)."""
    if not any(DATA_DIR.rglob("*.json")):
        pytest.skip("no data files")
    return load_store()
