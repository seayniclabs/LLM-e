"""Validation for the shared LLM-e contract: provider profile, model registry and
registry signature metadata.

The JSON Schemas in ``schemas/`` are the contract. Host apps in other languages
(Sonique, in Swift) validate against the same files. This module adds the checks
JSON Schema cannot express: unique ids and tags, roles that point at real targets,
and a signature sidecar whose sha256 matches the registry bytes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, List

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
PROFILE_SCHEMA_PATH = SCHEMA_DIR / "provider-profile.schema.json"
REGISTRY_SCHEMA_PATH = SCHEMA_DIR / "model-registry.schema.json"
SIGNATURE_SCHEMA_PATH = SCHEMA_DIR / "registry-signature.schema.json"

def _load_validator(path: Path) -> Draft202012Validator:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _schema_errors(validator: Draft202012Validator, data: Any) -> List[str]:
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"{location}: {err.message}")
    return errors


def _duplicates(values: Iterable[str]) -> List[str]:
    seen, dupes = set(), []
    for v in values:
        if v in seen and v not in dupes:
            dupes.append(v)
        seen.add(v)
    return dupes


def validate_profile(data: Any) -> List[str]:
    """Return a list of problems with a provider profile. Empty list means valid."""
    errors = _schema_errors(_load_validator(PROFILE_SCHEMA_PATH), data)
    if errors or not isinstance(data, dict):
        return errors

    ids = [t["id"] for t in data["targets"]]
    for dupe in _duplicates(ids):
        errors.append(f"targets: duplicate target id '{dupe}'")

    known = set(ids)
    roles = data["roles"]
    if roles["everyday"] not in known:
        errors.append(f"roles/everyday: '{roles['everyday']}' is not a target id")
    if roles["harder"] is not None and roles["harder"] not in known:
        errors.append(f"roles/harder: '{roles['harder']}' is not a target id")

    return errors


def validate_registry(data: Any) -> List[str]:
    """Return a list of problems with a model registry. Empty list means valid."""
    errors = _schema_errors(_load_validator(REGISTRY_SCHEMA_PATH), data)
    if errors or not isinstance(data, dict):
        return errors

    for dupe in _duplicates(m["id"] for m in data["models"]):
        errors.append(f"models: duplicate model id '{dupe}'")
    for dupe in _duplicates(m["tag"] for m in data["models"]):
        errors.append(f"models: duplicate tag '{dupe}'")
    return errors


def validate_signature_metadata(meta: Any, registry_bytes: bytes, require_signed: bool = False) -> List[str]:
    """Check signature sidecar metadata against the registry file it describes.

    This checks the metadata and the hash only. The CMS signature itself is
    verified by the host with Security.framework (Swift) or the security tool
    on macOS. See docs/host-apps.md. A production caller passes require_signed=True,
    so an "example-unsigned" sidecar is refused.
    """
    errors = _schema_errors(_load_validator(SIGNATURE_SCHEMA_PATH), meta)
    if errors or not isinstance(meta, dict):
        return errors
    if require_signed and meta.get("status") != "signed":
        errors.append(f"status: registry is {meta.get('status')!r}, not signed")

    actual = hashlib.sha256(registry_bytes).hexdigest()
    if actual != meta["sha256"]:
        errors.append(f"sha256: registry bytes hash to {actual}, metadata says {meta['sha256']}")
    return errors
