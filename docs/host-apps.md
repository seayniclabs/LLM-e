# LLM-e: notes for host apps

LLM-e finds, sets up and connects AI, then hands off. It never routes or proxies AI requests. A host app reads two things it produces or uses:

1. **Provider profile** (`schemas/provider-profile.schema.json`): the connections a person set up, which one handles everyday and harder questions, and the last test result.
2. **Model registry** (`schemas/model-registry.schema.json`): the list of recommended local models, with exact Ollama tags and licence notices. It ships signed with each release.

Sonique's provider adapters (FR-12) read the profile. Sonique's setup steps (FR-09) read the registry and write the profile. The Python `llme` package does the same in the stand-alone tool.

## Status

Phase 1 only. The schemas and sample files are the contract. The profile file location, the signing run and the Sonique adapters are not built yet. Items marked **proposal** need Sonique's sign-off.

## Files

| File | What it is |
|------|-----------|
| `schemas/provider-profile.schema.json` | Profile contract, schema version 1.x |
| `schemas/model-registry.schema.json` | Registry contract, schema version 1.x |
| `schemas/registry-signature.schema.json` | Sidecar metadata for the registry's detached signature |
| `schemas/examples/` | Valid samples, plus `invalid/` samples that must be rejected |
| `llme/schemas.py` | Python validation: schema plus checks JSON Schema cannot do |
| `tests/test_schemas.py` | Pytest suite (`uv run pytest`) |

Any language can validate against the JSON Schema files directly. Python-only checks are listed under "Checks beyond the schema".

## Reading the profile

- **Location (proposal):** `~/Library/Application Support/LLM-e/provider-profile.json`. Sonique confirms or changes this.
- **Validate first.** Reject a file that fails the schema. Show the person a plain message and a next step, never a crash.
- **Versions.** `schema_version` is `1.x.y`. A host supports major 1. A profile with another major is refused. Minor versions are additive, so a host should accept any 1.x it knows. Note that the schema sets `additionalProperties: false`, so a newer minor adds its fields with a new schema file, not silently.
- **Targets.** `kind` says what to call:
  - `ollama_local` and `ollama_remote`: an Ollama HTTP API at `endpoint`, model `model`. Use `model` exactly as written. It is the tag read from `/api/tags`.
  - `apple_intelligence`: no endpoint, no model. Use the system framework if available.
  - `openai_compatible`, `anthropic`, `openrouter`: an HTTPS `endpoint`, a `model`, and a `key_ref`.
- **Keys.** The profile never holds a key. For cloud targets, read the key from the macOS Keychain generic-password item named by `key_ref.service` and `key_ref.account`. Never log it, never write it back to the profile.
- **Roles.** `roles.everyday` is the target for everyday questions. `roles.harder` is the target for harder ones, or `null`. Both are target ids.
- **Test results.** `last_test` is `ok` or `failed`, with a plain `reason`. Show it as is. If `last_test` is `null`, the target has not been tested.
- **Contact rules.** Contact only addresses in the profile whose `source` is `network_scan` or `typed_address` (for remote Ollama) and the fixed endpoints for cloud targets. Never probe other addresses.

## Checks beyond the schema (Python, `llme.schemas`)

- Target ids are unique.
- `roles.everyday` and `roles.harder` name existing target ids.
- Registry model ids and tags are unique.
- Signature metadata `sha256` equals the SHA-256 of the registry file's exact bytes.

Swift hosts should reproduce these four checks.

## Verifying the registry before use

The registry is shipped with two files: `model-registry.json` and a detached CMS (PKCS#7) signature `model-registry.json.p7s`, plus `model-registry.signature.json` (the metadata above).

1. Check the metadata against the schema.
2. Hash the registry file's bytes and compare with `sha256`.
3. Verify the `.p7s` detached signature against those bytes. Check that the signer is `Developer ID Application: Charles Seay (7NSS5CJL9E)` and team `7NSS5CJL9E`. Swift: `SecCMSDecoder` / `SecCMSVerify`. macOS shell: `security cms -D` with the content file. Confirm the exact flags on a Mac before the first real signing.
4. If any step fails, do not use the registry. Keep the last good copy, or fall back to the registry bundled with the app, and tell the person the list could not be verified.

Sonique should pin the signer's certificate fingerprint (`signer.certificate_sha256` in the metadata) rather than trusting any certificate that chains to Apple.

## Producing the signature (not yet run)

Nothing is signed in this repo. Signing uses Charlie's Developer ID Application certificate (`7NSS5CJL9E`), which lives in his login Keychain, so the step runs on his Mac, not in CI.

1. Finalise `model-registry.json`, then compute its SHA-256.
2. Produce the detached CMS signature with the Developer ID identity: `security cms -S -N "Developer ID Application: Charles Seay (7NSS5CJL9E)" -d -i model-registry.json -o model-registry.json.p7s` (confirm flags first).
3. Write `model-registry.signature.json` with the hash, the signing time, the certificate fingerprint, and `status: "signed"`.
4. Run the verification steps above against the release files, then publish all three with the release.

Samples in `schemas/examples/` are marked `example-unsigned` and must never ship as release files.

## Versioning policy

- Patch: wording of messages, no field changes.
- Minor: new optional fields or new kinds, in a new schema file.
- Major: anything that changes meaning. Hosts refuse what they do not know.
- Registry: `registry_version` is calendar-style (`2026.10.1`). The profile records which registry version it was recommended from.

## Notes for Sonique

- The profile is plain JSON, so the person can read, edit or delete it. Keep it that way.
- Licence notices: show `licence.notice_text` wherever the model is named when `notice_required` is true (for example Llama's "Built with Llama").
- Remote Ollama is unauthenticated. Warn when an endpoint is not on the local network.
