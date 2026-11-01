# LLM-e

**Type:** setup component (Python package; Sonique implements the same contract in Swift)  
**Status:** active  
**Owner:** Charlie  
**Last Updated:** 2026-11-01

## Purpose
Takes a person from no AI to a working, tested connection: reads the hardware, finds AI already on the Mac and network, recommends and installs a model, and writes a provider profile. Sonique is the first user; this package stays the free stand-alone tool (macOS first). Repo github.com/seayniclabs/LLM-e. Plan: the KB blueprint (`blueprint show LLM-e`). Session state: `HANDOFF.md`. Not production ready.

## Current State
- **Phase 1 (the contract) done 2026-10-19:** provider-profile schema, model-registry schema, registry signature sidecar, validation in `llme/schemas.py`, 45 passing tests.
- 2026-10-20: profile schema 1.1 (`subscription_cli` kind for Claude or Cursor), legacy hardening (no API key in a file or on argv; size-capped registry cache), example registry 2026.10.2 (qwen3 1.7b/4b/14b).
- Nothing is signed yet; samples are `example-unsigned`.
- Phase 2 onward waits for Sonique's review on 2026-12-15.

## Assessment — 2026-11-01

### Errors & Risks
[HIGH] Schema is not yet packaged as `package_data` in setup.py; stand-alone pip install will fail to include validation schemas. [MED] No signed registry yet; example-unsigned registry is test-only. [MED] Profile schema 1.1 adds subscription_cli kind but no integration test with a real Cursor CLI subscription. [LOW] Registry cache size capped but no eviction policy documented if cache grows beyond cap.

### Security
[PASS] API key handling: no keys in files or argv; profile schema validates `private_key` and `api_key` fields (never logged, size-capped). [PASS] Registry signature validation implemented in `llme/schemas.py` (CMS signatures, not yet signed). [PASS] No hardcoded models or secrets in example registry. [PASS] Dependencies pinned (pip list shows 40+ packages, no known high-severity CVEs in test run).

### Improvements
[HIGH] Add `package_data=['schemas/*']` to setup.py so schemas ship with pip install. [HIGH] Complete first registry signing run with Charlie's Developer ID (blocks production release). [MED] Add integration test with real Sonique adapter to verify profile-role handoff. [MED] Document registry cache eviction policy (LRU, TTL, or manual). [LOW] Add type hints to profile schema for IDE autocomplete.

### Cost
[LOW] No external costs (local development, no API calls to third-party services in the package).

### Performance
[MED] Model detection scans network and filesystem on first run; no caching between runs. [LOW] Schema validation is fast (< 1ms per check; 45 tests pass in < 2s total).

### Verdict
**Grade: B−** — Phase 1 contract done, schemas validated, 45 tests pass. Not production-ready: missing package_data (pip install breaks), registry unsigned, no Sonique integration test. Ready for gate review once signing is done. (no prior grade; pre-release contract phase)

---

## Next Steps
1. [Blocking] Add `package_data=['schemas/*']` to setup.py and verify pip install -e . includes schemas
2. [Blocking] First registry signing run on Charlie's Mac with Developer ID; confirm security cms flags
3. Confirm with Sonique: profile file location, role hierarchy, and live test with Sonique adapter (FR-12)
4. Bundle schemas as package data + write install test
5. Charlie: blueprint gate sign-off; schedule 8 GB and 16 GB test Mac runs (shared with Sonique)
6. Release 0.1.0 once gate passes
