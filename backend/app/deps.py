"""Shared dependencies. Owned by Stream A."""
import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "contract" / "fixtures"
CATALOG_DIR = REPO_ROOT / "public_catalog"
DATA_DIR = REPO_ROOT / "data"


@lru_cache
def fixture(name: str) -> dict:
    """Contract fixture for an endpoint. Stub routers return these until the real implementation lands."""
    return json.loads((FIXTURES / f"{name}.json").read_text())
