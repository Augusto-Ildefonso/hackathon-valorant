import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.data.catalog import get_catalog
from app.main import app

client = TestClient(app)


def _jett_url():
    jett = next(a for a, (_, n) in get_catalog()._agents.items() if n == "Jett")
    return get_catalog().agent(jett).icon_url


def test_agent_thumbnail_is_small():
    r = client.get(_jett_url())
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    im = Image.open(io.BytesIO(r.content))
    assert im.width == 96 and len(r.content) < 60_000  # the original is 1024px / ~850 KB


def test_weapon_and_map_thumbnails():
    cat = get_catalog()
    w = next(w for w, (_, n) in cat._weapons.items() if n == "Vandal")
    assert client.get(cat.weapon(w).icon_url).status_code == 200
    assert client.get(cat.map_ref("Ascent").thumb_url).status_code == 200


@pytest.mark.parametrize("path", [
    "/api/thumb/Secrets/abc", "/api/thumb/Characters/does-not-exist", "/api/thumb/Characters/..%2Fcatalog",
    "/api/thumb/Characters/ADD6443A-41BD-E414-F6AD-E58D267F4E95?w=4",
])
def test_bad_requests_are_rejected(path):
    assert client.get(path).status_code in (404, 422)
