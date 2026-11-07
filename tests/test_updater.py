"""The registry refresh: the URL points at this repository, and the cache lives with the user."""

import io
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from llme import updater

ROOT = Path(__file__).resolve().parent.parent


def test_the_registry_url_points_at_this_repository():
    # The regression this guards: the URL used to name "seayniclabs/llm-me", which 404s, so the
    # weekly refresh failed on every machine and the registry never updated itself.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    repo = re.sub(r"\.git$", "", re.search(r"github\.com/([\w.-]+/[\w.-]+)", readme).group(1))
    assert updater.REGISTRY_URL == f"https://raw.githubusercontent.com/{repo}/main/llme/registry.json"
    assert updater.REPOSITORY == repo


def test_the_cache_is_not_inside_the_installation():
    package_dir = Path(updater.__file__).resolve().parent
    cache_path = Path(updater.CACHE_FILE).resolve()
    assert package_dir not in cache_path.parents
    assert cache_path.name == "registry.json"


def test_cache_dir_honours_llme_cache_dir():
    out = subprocess.run(
        [sys.executable, "-c", "from llme import updater; print(updater.CACHE_FILE)"],
        capture_output=True, text=True, env={**os.environ, "LLME_CACHE_DIR": "/tmp/llme-test-cache"},
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "/tmp/llme-test-cache/registry.json"


def test_cache_dir_honours_xdg_cache_home():
    env = {**os.environ, "XDG_CACHE_HOME": "/tmp/xdg-test"}
    env.pop("LLME_CACHE_DIR", None)
    out = subprocess.run([sys.executable, "-c", "from llme import updater; print(updater.cache_dir())"],
                         capture_output=True, text=True, env=env)
    assert out.returncode == 0, out.stderr
    if sys.platform.startswith("linux"):
        assert out.stdout.strip() == "/tmp/xdg-test/llme"
    else:  # macOS and Windows have their own cache roots, which the env var does not override
        assert out.stdout.strip() != "/tmp/xdg-test/llme"


class Resp(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def cache(tmp_path, monkeypatch):
    path = tmp_path / "cache" / "registry.json"
    monkeypatch.setattr(updater, "CACHE_FILE", str(path))
    return path


def test_a_legacy_package_cache_is_moved_across_with_its_age(tmp_path, cache, monkeypatch):
    legacy = tmp_path / "legacy-registry.json"
    legacy.write_text(json.dumps({"cloud": [], "local": [{"name": "old"}]}))
    os.utime(legacy, (0, 0))
    monkeypatch.setattr(updater, "LEGACY_CACHE_FILE", str(legacy))
    monkeypatch.setattr(updater.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))

    assert updater.get_registry() == {"cloud": [], "local": [{"name": "old"}]}
    assert cache.exists()
    # The age comes with it, so the copy is still due for a refresh rather than looking fresh.
    assert os.path.getmtime(cache) == 0


def test_migration_never_overwrites_a_cache_the_user_already_has(tmp_path, cache, monkeypatch):
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"cloud": [], "local": [{"name": "new"}]}))
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"cloud": [], "local": [{"name": "old"}]}))
    monkeypatch.setattr(updater, "LEGACY_CACHE_FILE", str(legacy))

    assert updater.get_registry()["local"] == [{"name": "new"}]


def test_a_stale_cache_is_replaced_by_the_fetched_registry(cache, monkeypatch):
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"cloud": [], "local": [{"name": "stale"}]}))
    os.utime(cache, (0, 0))
    fresh = {"cloud": [{"name": "cloud"}], "local": [{"name": "fresh"}]}
    monkeypatch.setattr(updater.urllib.request, "urlopen",
                        lambda *a, **k: Resp(json.dumps(fresh).encode()))

    assert updater.get_registry() == fresh
    assert json.loads(cache.read_text()) == fresh
    assert not (Path(str(cache) + ".tmp")).exists()      # no half-written file left behind


def test_a_fresh_cache_is_not_fetched_again(cache, monkeypatch):
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"cloud": [], "local": [{"name": "cached"}]}))

    def explode(*args, **kwargs):
        raise AssertionError("a fresh cache must not trigger a fetch")

    monkeypatch.setattr(updater.urllib.request, "urlopen", explode)
    assert updater.get_registry()["local"] == [{"name": "cached"}]


def test_a_stale_cache_survives_a_failed_fetch(cache, monkeypatch, caplog):
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"cloud": [], "local": [{"name": "last-good"}]}))
    os.utime(cache, (0, 0))
    monkeypatch.setattr(updater.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("connection refused")))

    assert updater.get_registry()["local"] == [{"name": "last-good"}]
    assert "connection refused" in caplog.text
    assert updater.REGISTRY_URL in caplog.text        # the log names what could not be fetched


def test_the_shipped_registry_is_plausible():
    shipped = json.loads((ROOT / "llme" / "registry.json").read_text(encoding="utf-8"))
    assert updater._plausible(shipped)
    assert shipped["local"] and shipped["cloud"]
