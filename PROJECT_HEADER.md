# LLM-e

**Type:** setup component (Python package; Sonique implements the same contract in Swift)  
**Status:** active  
**Owner:** Charlie  
**Last Updated:** 2026-10-20

## Purpose
Takes a person from no AI to a working, tested connection: reads the hardware, finds AI already on the Mac and network, recommends and installs a model, and writes a provider profile. Sonique is the first user; this package stays the free stand-alone tool (macOS first). Repo github.com/seayniclabs/LLM-e. Plan: the KB blueprint (`blueprint show LLM-e`). Session state: `HANDOFF.md`. Not production ready.

## Current State
- **Phase 1 (the contract) done 2026-10-19:** provider-profile schema, model-registry schema, registry signature sidecar, validation in `llme/schemas.py`, 45 passing tests.
- 2026-10-20: profile schema 1.1 (`subscription_cli` kind for Claude or Cursor), legacy hardening (no API key in a file or on argv; size-capped registry cache), example registry 2026.10.2 (qwen3 1.7b/4b/14b).
- Nothing is signed yet; samples are `example-unsigned`.
- Phase 2 onward waits for Sonique's review on 2026-12-15.

## Next Steps
1. First registry signing run on Charlie's Mac with his Developer ID (confirm the `security cms` flags first), after checking each sample model's licence and size against the vendor page
2. Confirm with Sonique: profile file location and profile-level roles (FR-12 adapter design)
3. Bundle `schemas/` as package data before any stand-alone release
4. Charlie: blueprint gate sign-off; 8 GB and 16 GB test Macs (shared with Sonique)
