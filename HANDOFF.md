# LLM-e Handoff

**Project:** LLM-e (LLM+Me) · **Repo:** `~/Projects/LLM-e` · **GitHub:** `seayniclabs/LLM-e` · **CMDB project:** `LLM-e`
**Last updated:** 2026-10-19 · **Status:** active, reshaped; Phase 1 contract done (2026-10-19). Not production ready.

## Source of truth
Scope, phases, decisions and kill rules live only in the blueprint: `blueprint show LLM-e` (Bridge → `/blueprint/LLM-e`). If this file disagrees, the blueprint wins.

## What this is now (2026-10-19)
A reusable AI-setup component: it takes a person from no AI to a working, tested connection. It reads the hardware, finds AI already on the Mac and network (Ollama locally, Ollama on found or typed devices, Apple Intelligence), recommends and installs a local model, adds cloud providers (keys in the Keychain), tests each connection, and writes one versioned profile file that host apps read. It sets up and hands off; it never routes AI traffic.

Sonique is the first user: Sonique implements these steps in Swift against a shared schema and signed model registry. This Python package stays the free stand-alone tool (macOS first) for GitHub and seayniclabs.com.

Earlier on 2026-10-19 it was scrapped as a stand-alone MCP product ("not an MCP, packaging broken, crowded market"); the reshape replaces that.

## What exists (and what's wrong with it)
- `llme/`: about 960 lines of Python. Hardware scan with GPU detection (`scanner.py`, `gpu_scanner.py`), local and cloud recommendations (`discovery_local.py`, `discovery_cloud.py`, `registry.json`, `models.json`, `updater.py`), Ollama install and model pull (`installer.py`), benchmark (`benchmarker.py`), HTML report (`instructions.py`), CLI (`cli.py`). The enhancement suite (task #1835) added GPU detection, install automation and benchmarking.
- Known problems: packaging is broken; Ollama is localhost-only; OpenRouter is the only cloud provider; model lists go stale; keys are taken on the command line; no profile schema.
- The previous version of this file said "production ready", which was not accurate.

## Phase 1 (done 2026-10-19): the contract
- `schemas/provider-profile.schema.json` (profile, schema 1.x): targets by kind (`ollama_local`, `ollama_remote`, `apple_intelligence`, `openai_compatible`, `anthropic`, `openrouter`); exact Ollama tag; Keychain `key_ref` (service/account, never the key; `additionalProperties: false` blocks inline keys); `last_test` (ok/failed, plain reason, timestamp); `performance` (tokens/s, time to first token); `roles` (everyday, harder).
- `schemas/model-registry.schema.json` (registry, calendar version `2026.10.1`): per model: exact tag, family, size on disk, min memory, acceleration, licence id with `notice_required` and `notice_text`, recommended-for notes.
- `schemas/registry-signature.schema.json`: detached CMS signature sidecar metadata (sha256 of registry bytes, signer pinned to Developer ID Application, Charles Seay, team 7NSS5CJL9E).
- `llme/schemas.py`: validation (schema plus unique ids/tags, roles resolve to targets, sha256 match). `tests/test_schemas.py`: 45 pytest tests, all passing (`uv run pytest`). Samples in `schemas/examples/`, invalid ones in `schemas/examples/invalid/`.
- `docs/host-apps.md`: what Sonique's adapters read, verification steps, signing procedure, versioning policy.
- Dependencies: `jsonschema` (runtime), `pytest` (dev group). `pyproject.toml` pins `[tool.setuptools] packages = ["llme"]` because the new `schemas/` and existing `Lessons/` dirs broke flat-layout discovery (`uv add` failed to build).

## Open (Phase 1)
1. **Nothing is signed.** Samples are `example-unsigned`. The release signing run happens on Charlie's Mac (Keychain identity). `security cms` flags need confirming on a Mac before the first real signature.
2. **Profile file location** is a proposal (`~/Library/Application Support/LLM-e/provider-profile.json`). Sonique to confirm.
3. **Registry content** in the samples (three models, sizes, memory minimums, licence URLs) is illustrative. Verify each against the vendor's licence and model page before signing.
4. Schemas are read from `../schemas` relative to the package. Bundle them as package data before a stand-alone release.
5. Roles are profile-level (`roles.everyday`, `roles.harder`), not per target. Confirm with Sonique's FR-12 adapter design.
6. Swift parity checks (the four Python-only checks in `docs/host-apps.md`) belong to Sonique.

## Next
1. Phase 2 and later wait for Sonique's review on 2026-12-15 (discovery, installer, UI, Swift setup). Nothing from them is started here.
2. Charlie: 8 GB and 16 GB test Macs (shared with Sonique T1); sign-off on the blueprint gate; Office Hours doc.
3. Registry signing key: Charlie's Developer ID (decided 2026-10-19).
