"""Validation tests for the LLM-e profile, registry and signature contract."""

import copy
import json
from pathlib import Path

import pytest

from llme.schemas import (
    PROFILE_SCHEMA_PATH,
    REGISTRY_SCHEMA_PATH,
    SIGNATURE_SCHEMA_PATH,
    validate_profile,
    validate_registry,
    validate_signature_metadata,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "schemas" / "examples"
INVALID = EXAMPLES / "invalid"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def target(profile, tid):
    return next(t for t in profile["targets"] if t["id"] == tid)


@pytest.fixture
def profile():
    return load(EXAMPLES / "profile.valid.json")


@pytest.fixture
def registry():
    return load(EXAMPLES / "registry.valid.json")


# --- schema files themselves -------------------------------------------------

@pytest.mark.parametrize("path", [PROFILE_SCHEMA_PATH, REGISTRY_SCHEMA_PATH, SIGNATURE_SCHEMA_PATH])
def test_schema_files_are_valid_draft_2020_12(path):
    from jsonschema import Draft202012Validator

    Draft202012Validator.check_schema(load(path))


def test_schemas_are_versioned_in_their_ids():
    # Profile schema 1.1 adds the subscription_cli kind (additive minor). Registry and signature stay at 1.0.
    assert "-1.1" in load(PROFILE_SCHEMA_PATH)["$id"]
    for path in [REGISTRY_SCHEMA_PATH, SIGNATURE_SCHEMA_PATH]:
        assert "-1.0" in load(path)["$id"]


# --- valid samples -----------------------------------------------------------

def test_valid_profile_sample_passes(profile):
    assert validate_profile(profile) == []


def test_valid_registry_sample_passes(registry):
    assert validate_registry(registry) == []


def test_valid_signature_sample_matches_registry_bytes(registry):
    raw = (EXAMPLES / "registry.valid.json").read_bytes()
    meta = load(EXAMPLES / "registry-signature.valid.json")
    assert validate_signature_metadata(meta, raw) == []


def test_profile_covers_every_target_kind(profile):
    kinds = {t["kind"] for t in profile["targets"]}
    assert kinds >= {"ollama_local", "ollama_remote", "apple_intelligence", "openrouter"}


def test_profile_schema_lists_all_required_kinds():
    kinds = load(PROFILE_SCHEMA_PATH)["$defs"]["target"]["properties"]["kind"]["enum"]
    assert set(kinds) == {
        "ollama_local",
        "ollama_remote",
        "apple_intelligence",
        "openai_compatible",
        "anthropic",
        "openrouter",
        "subscription_cli",
    }


def test_valid_subscription_profile_sample_passes():
    profile = load(EXAMPLES / "profile.subscription.valid.json")
    assert validate_profile(profile) == []
    assert {t["cli"] for t in profile["targets"] if t["kind"] == "subscription_cli"} == {"claude", "cursor"}


def test_subscription_target_takes_no_key_and_no_address(profile):
    profile = load(EXAMPLES / "profile.subscription.valid.json")
    t = target(profile, "claude-subscription")
    t["key_ref"] = {"service": "com.seaynic.llme.provider", "account": "anthropic"}
    assert validate_profile(profile)
    t["key_ref"] = None
    t["endpoint"] = "https://api.anthropic.com"
    assert validate_profile(profile)


def test_cli_field_is_only_for_subscription_targets(profile):
    profile = copy.deepcopy(profile)
    target(profile, "openrouter-main")["cli"] = "claude"
    assert validate_profile(profile)


def test_subscription_target_needs_a_known_cli():
    profile = load(EXAMPLES / "profile.subscription.valid.json")
    target(profile, "claude-subscription")["cli"] = "codex"
    assert validate_profile(profile)


# --- invalid samples: every file must fail -----------------------------------

def _invalid_files(prefix):
    return sorted(INVALID.glob(f"{prefix}*.json"))


PROFILE_INVALID = _invalid_files("profile-")
REGISTRY_INVALID = _invalid_files("registry-")
SIGNATURE_INVALID = _invalid_files("signature-")


def test_invalid_sample_set_is_complete():
    assert len(PROFILE_INVALID) >= 10
    assert len(REGISTRY_INVALID) >= 4
    assert len(SIGNATURE_INVALID) >= 3


@pytest.mark.parametrize("path", PROFILE_INVALID, ids=lambda p: p.name)
def test_invalid_profile_is_rejected(path):
    assert validate_profile(load(path)), f"{path.name} should be rejected"


@pytest.mark.parametrize("path", REGISTRY_INVALID, ids=lambda p: p.name)
def test_invalid_registry_is_rejected(path):
    assert validate_registry(load(path)), f"{path.name} should be rejected"


@pytest.mark.parametrize("path", SIGNATURE_INVALID, ids=lambda p: p.name)
def test_invalid_signature_is_rejected(path):
    raw = (EXAMPLES / "registry.valid.json").read_bytes()
    assert validate_signature_metadata(load(path), raw), f"{path.name} should be rejected"


# --- specific rules, with the reason checked --------------------------------

def test_inline_key_is_rejected_as_unknown_field(profile):
    profile["targets"][3]["api_key"] = "x"
    errors = validate_profile(profile)
    assert any("api_key" in e or "Additional properties" in e for e in errors)


def test_profile_has_no_field_that_could_hold_a_key(profile):
    schema = load(PROFILE_SCHEMA_PATH)
    target_props = schema["$defs"]["target"]["properties"]
    assert not any("key" in name and name != "key_ref" for name in target_props)
    assert schema["$defs"]["target"]["additionalProperties"] is False
    assert schema["$defs"]["keyRef"]["additionalProperties"] is False


def test_ollama_tag_must_include_version(profile):
    profile = copy.deepcopy(profile)
    target(profile, "this-mac-ollama")["model"] = "llama3.2"
    assert any("model" in e for e in validate_profile(profile))


def test_cloud_target_needs_key_reference(profile):
    profile = copy.deepcopy(profile)
    target(profile, "openrouter-main")["key_ref"] = None
    assert any("key_ref" in e for e in validate_profile(profile))


def test_cloud_endpoint_must_be_https(profile):
    profile = copy.deepcopy(profile)
    target(profile, "openrouter-main")["endpoint"] = "http://openrouter.ai/api/v1"
    assert validate_profile(profile)


def test_local_ollama_must_be_on_this_mac(profile):
    profile = copy.deepcopy(profile)
    target(profile, "this-mac-ollama")["endpoint"] = "http://192.168.1.99:11434"
    assert validate_profile(profile)


def test_remote_ollama_must_be_found_or_typed(profile):
    profile = copy.deepcopy(profile)
    target(profile, "study-ollama")["source"] = "manual"
    assert validate_profile(profile)


def test_apple_intelligence_has_no_endpoint_or_key(profile):
    profile = copy.deepcopy(profile)
    target(profile, "apple-intelligence")["endpoint"] = "http://localhost:11434"
    assert validate_profile(profile)


def test_test_result_status_is_ok_or_failed(profile):
    profile = copy.deepcopy(profile)
    target(profile, "this-mac-ollama")["last_test"]["status"] = "maybe"
    assert validate_profile(profile)


def test_failed_test_still_needs_plain_reason(profile):
    profile = copy.deepcopy(profile)
    del target(profile, "study-ollama")["last_test"]["reason"]
    assert validate_profile(profile)


def test_profile_major_version_must_be_1(profile):
    profile = copy.deepcopy(profile)
    profile["schema_version"] = "2.0.0"
    assert any("schema_version" in e for e in validate_profile(profile))


def test_roles_must_point_at_existing_targets(profile):
    profile = copy.deepcopy(profile)
    profile["roles"]["everyday"] = "nope"
    assert any("roles/everyday" in e for e in validate_profile(profile))


def test_harder_role_may_be_null(profile):
    profile = copy.deepcopy(profile)
    profile["roles"]["harder"] = None
    assert validate_profile(profile) == []


def test_unknown_top_level_field_rejected(profile):
    profile["telemetry"] = {"enabled": True}
    assert validate_profile(profile)


def test_notice_required_needs_notice_text(registry):
    registry = copy.deepcopy(registry)
    registry["models"][0]["licence"]["notice_text"] = None
    assert any("notice_text" in e for e in validate_registry(registry))


def test_registry_ids_and_tags_are_unique(registry):
    registry = copy.deepcopy(registry)
    registry["models"][1]["id"] = registry["models"][0]["id"]
    assert any("duplicate model id" in e for e in validate_registry(registry))


def test_signature_hash_must_match_registry_bytes(registry):
    meta = load(EXAMPLES / "registry-signature.valid.json")
    tampered = (EXAMPLES / "registry.valid.json").read_bytes().replace(b"8", b"9", 1)
    assert any("sha256" in e for e in validate_signature_metadata(meta, tampered))


def test_signer_is_pinned_to_developer_id():
    schema = load(SIGNATURE_SCHEMA_PATH)
    signer = schema["properties"]["signer"]["properties"]
    assert signer["identity"]["const"] == "Developer ID Application: Charles Seay (7NSS5CJL9E)"
    assert signer["team_id"]["const"] == "7NSS5CJL9E"
