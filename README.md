# LLM-e

Takes you from "no AI" to a working, tested model connection: reads your hardware, finds AI
already on your Mac and network, recommends a model that fits, installs it, and writes a
provider profile other tools can use. macOS first. Sonique uses the same profile contract.

> Status: pre-release (0.1.0). The model registry samples are unsigned examples; there is no
> PyPI release yet.

## Install (from source)

```bash
git clone https://github.com/seayniclabs/LLM-e.git
cd LLM-e
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Use

```bash
.venv/bin/llme scan                      # hardware scan + recommendation report (default)
.venv/bin/llme install --local qwen3:4b  # install Ollama and pull a model
.venv/bin/llme benchmark qwen3:4b        # measure local inference speed
.venv/bin/llme update-models             # validate and refresh the cloud model registry
```

`scan` writes `llme_system_config.json` and `llme_report.html` in the current directory. Both
describe your hardware and stay local.

## Provider profiles

The profile and model-registry formats are JSON Schemas in [`schemas/`](schemas/), with valid
and invalid examples. API keys are never stored in a profile; a profile holds a reference to a
key kept in the system keychain.

## Tests

```bash
.venv/bin/pip install pytest && .venv/bin/python -m pytest -q
```
