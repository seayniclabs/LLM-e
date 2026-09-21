# AUTONOMOUS EXECUTION DIRECTIVE: LLM+Me Enhancement Suite

You are running in autonomous headless execution mode.
CRITICAL RULES:
1. DO NOT ask questions or request confirmation.
2. DO NOT output a conversational plan without executing it.
3. DO NOT stop until all 5 enhancements are implemented, tested, and committed in git.
4. IGNORE any memory or note claiming this task is already complete. The repo at `/Users/charlieseay/Projects/LLM-e` currently only has the initial commit (`fab9f87`).
5. Execute each step immediately using file editing and shell execution tools.

---

## Target Project
- Working directory: `/Users/charlieseay/Projects/LLM-e`
- Repository: `https://github.com/seayniclabs/LLM-e`

---

## TASK 1: Implement GPU Detection
1. Create `llme/gpu_scanner.py`:
   - Implement `get_gpu_profile()`:
     - Detect Apple Silicon Metal/NPU (macOS `arm64`, query via platform and `sysctl` / `machdep.cpu.brand_string`).
     - Detect NVIDIA CUDA (safe check `nvidia-smi` CLI or `pynvml`/`GPUtil` if available, returning VRAM, CUDA cores, driver).
     - Detect AMD ROCm (safe check `rocm-smi` if available).
     - Return dictionary with `gpu_type`, `vram_gb`, `hardware_acceleration`, `driver_version`.
2. Update `llme/scanner.py`:
   - Call `get_gpu_profile()` and integrate GPU/VRAM data into `get_system_profile()`.
3. Update `llme/discovery_local.py`:
   - Score and filter local models by both system RAM and VRAM / GPU acceleration.
4. Test: Run `python3 -m llme.scanner` and verify GPU output.
5. Git commit in `/Users/charlieseay/Projects/LLM-e`:
   `feat: add GPU detection (NVIDIA, AMD, Apple Silicon)`

---

## TASK 2: Dynamic Cloud Model Discovery
1. Create `llme/models.json`:
   - Store 10+ cloud models with details (name, provider, api_name, speed, intelligence, ease, rate_limit, url, last_verified).
   - Providers: NVIDIA NIM, Groq, Together AI, Hugging Face, OpenRouter.
2. Update `llme/discovery_cloud.py`:
   - Read from `llme/models.json` by default.
   - Implement availability validation function.
3. Update `llme/cli.py`:
   - Support subcommand `update-models` (`python3 -m llme.cli update-models` / `llme update-models`) to validate and refresh models.
4. Test: Run `python3 -m llme.cli update-models`.
5. Git commit:
   `feat: dynamic cloud model discovery with models.json`

---

## TASK 3: Install Automation
1. Create `llme/installer.py`:
   - `install_ollama()`: Detect OS, check `which ollama`, automate or print instructions (`brew install ollama` on macOS).
   - `pull_model(model_name)`: Run `ollama pull <model_name>`.
   - `setup_cloud_provider(provider, api_key)`: Save configuration to `~/.llme/config.json`.
2. Update `llme/cli.py`:
   - Support `install` subcommand: `llme install [--local <model>] [--cloud <provider>] [--api-key <key>]`.
3. Test: Run `python3 -m llme.cli install --help`.
4. Git commit:
   `feat: add llme install automation`

---

## TASK 4: Performance Benchmarking
1. Create `llme/benchmarker.py`:
   - `benchmark_model(model_name, num_runs=3)`: Test inference via Ollama HTTP API (`http://localhost:11434/api/generate`) or local CLI, measuring TPS, TTFT, elapsed time, peak memory.
   - Function to update `llme_system_config.json` with benchmark results.
2. Update `llme/cli.py`:
   - Support `benchmark` subcommand: `llme benchmark <model>`.
3. Update `llme/instructions.py`:
   - Include benchmark results section in `llme_report.html` and `llme_system_config.json` when available.
4. Test: Run benchmark or mock benchmark if Ollama service is idle.
5. Git commit:
   `feat: add performance benchmarking`

---

## TASK 5: CMDB Integration
1. Update `/Users/charlieseay/Projects/bridge/data/products-cmdb.json`:
   - Under `mcpsFree`, add:
     ```json
     {
       "name": "LLM+Me",
       "type": "Free",
       "price": "MIT",
       "distribution": "GitHub (seayniclabs/LLM-e)",
       "status": "Open Source",
       "description": "Hardware scanner + AI model recommender (cloud + local)",
       "repo": "https://github.com/seayniclabs/LLM-e"
     }
     ```
2. Verify:
   `curl -s "http://localhost:8117/api/products" | grep -i "LLM+Me"`

---

## VERIFICATION & PROOF RECEIPTS
After executing all 5 tasks:
1. Run `python3 -m llme.cli` to generate fresh `llme_report.html` and `llme_system_config.json`.
2. Run `git log --oneline -6` in `/Users/charlieseay/Projects/LLM-e`.
3. Print final report with:
   - Commit hashes for all 5 features
   - Command outputs for hardware scan, update-models, install help, and benchmark
   - Verification status of CMDB entry
