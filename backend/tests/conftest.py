import pytest


@pytest.fixture(autouse=True)
def llm_off_by_default(monkeypatch):
    """The LLM is on whenever a key exists, so a developer's real .env key must not make tests call the API."""
    monkeypatch.setenv("VAVAGYM_LLM", "0")

from app.data.loader import load_store
from app.deps import DATA_DIR


@pytest.fixture(scope="session")
def full_store():
    """The real dataset (cached on disk by the loader)."""
    if not any(DATA_DIR.rglob("*.json")):
        pytest.skip("no data files")
    return load_store()
