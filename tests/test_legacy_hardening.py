"""Legacy (pre-Phase-1) modules: keys never reach a file or argv; a bad remote registry never replaces the cache."""
import io
import json
import os
import stat
from pathlib import Path

from llme import cli, installer, updater
from llme.schemas import validate_signature_metadata

EXAMPLES = Path(__file__).resolve().parent.parent / "schemas" / "examples"


def test_install_has_no_api_key_flag():
    actions = [a for p in cli.build_parser()._subparsers._group_actions for sp in p.choices.values() for a in sp._actions]
    assert not any("--api-key" in a.option_strings for a in actions)


def test_cloud_provider_writes_only_a_keychain_reference(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"providers": {"openrouter": {"api_key": "sk-old-plaintext"}}}))
    monkeypatch.setattr(installer, "CONFIG_DIR", str(tmp_path)); monkeypatch.setattr(installer, "CONFIG_FILE", str(cfg))
    monkeypatch.setattr(installer.sys, "stdin", io.StringIO())          # not a tty: prints the security command, runs nothing
    calls = []; monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: calls.append(a))
    installer.setup_cloud_provider("openrouter")
    saved = json.loads(cfg.read_text())
    assert saved["providers"]["openrouter"] == {"key_ref": {"service": "com.seaynic.llme.provider.openrouter", "account": "default"}}
    assert "sk-old-plaintext" not in cfg.read_text()
    assert stat.S_IMODE(os.stat(cfg).st_mode) == 0o600 and calls == []
    assert installer.setup_cloud_provider("../evil") is None


def test_bad_remote_registry_keeps_the_cache(tmp_path, monkeypatch):
    cache = tmp_path / "registry.json"; good = {"cloud": [], "local": [{"name": "x"}]}
    cache.write_text(json.dumps(good)); os.utime(cache, (0, 0))          # stale, so a fetch is attempted

    class Resp(io.BytesIO):
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(updater, "CACHE_FILE", str(cache))
    for body in (b'{"evil": true}', b"not json", b"[" + b" " * (updater.MAX_BYTES + 10) + b"]"):
        monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *a, **k: Resp(body))
        assert updater.get_registry() == good
        os.utime(cache, (0, 0))


def test_require_signed_refuses_example_unsigned():
    raw = (EXAMPLES / "registry.valid.json").read_bytes()
    meta = json.loads((EXAMPLES / "registry-signature.valid.json").read_text())
    meta["status"] = "example-unsigned"
    assert validate_signature_metadata(meta, raw) == []
    assert any("not signed" in e for e in validate_signature_metadata(meta, raw, require_signed=True))
