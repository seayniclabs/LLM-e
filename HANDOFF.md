# LLM-e Handoff

**Project:** LLM-e (LLM+Me) · **Repo:** `~/Projects/LLM-e` · **GitHub:** `seayniclabs/LLM-e` · **CMDB project:** `LLM-e`
**Last updated:** 2026-10-19 · **Status:** active, reshaped. Not production ready.

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

## Next
1. **Phase 1 (allowed now):** profile schema (versioned JSON Schema) and model registry format, signed. Sonique's provider adapters (FR-12) read connections from it.
2. Everything else (discovery, installer, Swift setup in Sonique) waits for Sonique's Phase 2, after the 2026-12-15 review.
3. Open: which key signs the registry; 8/16 GB test Macs; Charlie's sign-off; an Office Hours doc for the gate.
