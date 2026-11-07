# LLM-e

Takes you from "no AI" to a working, tested model connection: reads your hardware, finds AI
already on your machine, recommends a model that fits, installs it, and writes a provider
profile other tools can use. macOS first. Sonique uses the same profile contract.

> Status: pre-release (0.1.0). The model registry samples are unsigned examples; there is no
> PyPI release yet.

## Install (from source)

```bash
git clone https://github.com/seayniclabs/LLM-e.git
cd LLM-e
python3 -m venv .venv
.venv/bin/pip install --upgrade pip   # macOS's bundled pip 21 can't install this project
.venv/bin/pip install -e .
```

## Use

```bash
.venv/bin/llme scan                      # hardware scan + recommendation report (default)
.venv/bin/llme inventory                 # model servers already running on this machine
.venv/bin/llme install --local qwen3:4b  # install Ollama and pull a model
.venv/bin/llme benchmark qwen3:4b        # measure local inference speed
.venv/bin/llme update-models             # validate and refresh the cloud model registry
```

`scan` writes `llme_system_config.json` and `llme_report.html` in the current directory. Both
describe your hardware and stay local.

### What is already here

`scan` also asks the usual local model servers what they hold, so the report does not recommend
downloading something you finished pulling last week. It probes localhost only, one short-timeout
request per port, and reports what answered:

| Server | Port | Endpoint |
|---|---|---|
| Ollama | 11434 | `/api/tags` |
| LM Studio | 1234 | `/v1/models` |
| vLLM | 8000 | `/v1/models` |
| llama.cpp server | 8080 | `/v1/models` |

`llme inventory` prints the same list on its own (`--json` for scripts, `--host`/`--timeout` to
probe elsewhere or wait longer), and `llme scan --no-probe` skips the check entirely.

## Registry cache

The model registry is refreshed from this repository when the local copy is older than a week,
and read from cache otherwise. The cache lives in the per-user cache directory
(`~/Library/Caches/llme` on macOS, `~/.cache/llme` on Linux, `%LOCALAPPDATA%\llme\cache` on
Windows), not in the installation, so it survives upgrades and works when the package is
installed read-only. `LLME_CACHE_DIR` overrides the location.

## Provider profiles

The profile and model-registry formats are JSON Schemas in [`schemas/`](schemas/), with valid
and invalid examples. API keys are never stored in a profile; a profile holds a reference to a
key kept in the system keychain.

## Tests

```bash
.venv/bin/pip install pytest && .venv/bin/python -m pytest -q
```

## Licence

MIT. See [LICENSE](LICENSE).
