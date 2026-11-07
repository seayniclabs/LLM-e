import json
import os
import time
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/generate"
BENCHMARK_PROMPT = "Explain what an operating system does in two sentences."
CONFIG_FILENAME = "llme_system_config.json"


def default_config_path(output_dir=None):
    """Where the benchmark result is merged: the directory you ran the command in, never the
    directory the process happened to start in at import time."""
    return os.path.join(output_dir or os.getcwd(), CONFIG_FILENAME)


def _single_run(model_name, prompt=BENCHMARK_PROMPT, timeout=120):
    payload = json.dumps({"model": model_name, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )

    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        return {"error": str(e)}
    elapsed = time.monotonic() - start

    # A port that answers is not necessarily Ollama: a login page, a proxy or a JSON error body
    # all arrive as 200. Say so, instead of raising out of the middle of a benchmark.
    try:
        body = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return {"error": "the server answered, but not with JSON"}
    if not isinstance(body, dict):
        return {"error": "the server answered with JSON that is not an object"}

    eval_count = body.get("eval_count")
    eval_duration_ns = body.get("eval_duration")
    prompt_eval_duration_ns = body.get("prompt_eval_duration")

    tps = None
    if eval_count and eval_duration_ns:
        tps = round(eval_count / (eval_duration_ns / 1e9), 2)

    ttft_s = round(prompt_eval_duration_ns / 1e9, 3) if prompt_eval_duration_ns else None

    return {
        "elapsed_s": round(elapsed, 3),
        "tokens_per_second": tps,
        "ttft_s": ttft_s,
        "eval_count": eval_count,
    }


def benchmark_model(model_name, num_runs=3):
    """
    Benchmarks a locally installed Ollama model by sending it a fixed prompt
    over the Ollama HTTP API and measuring tokens/sec, time-to-first-token,
    and total elapsed time across num_runs, then averaging the results.
    """
    if isinstance(num_runs, bool) or not isinstance(num_runs, int) or num_runs < 1:
        raise ValueError(f"num_runs must be a whole number of runs, 1 or more (got {num_runs!r})")

    runs = []
    for i in range(num_runs):
        result = _single_run(model_name)
        runs.append(result)
        if "error" in result:
            return {
                "model": model_name,
                "status": "unavailable",
                "error": result["error"],
                "hint": "Is Ollama running? Try `ollama serve` or check `ollama list`.",
            }

    valid_tps = [r["tokens_per_second"] for r in runs if r.get("tokens_per_second")]
    valid_ttft = [r["ttft_s"] for r in runs if r.get("ttft_s") is not None]
    valid_elapsed = [r["elapsed_s"] for r in runs if r.get("elapsed_s") is not None]

    return {
        "model": model_name,
        "status": "ok",
        "num_runs": num_runs,
        "avg_tokens_per_second": round(sum(valid_tps) / len(valid_tps), 2) if valid_tps else None,
        "avg_ttft_s": round(sum(valid_ttft) / len(valid_ttft), 3) if valid_ttft else None,
        "avg_elapsed_s": round(sum(valid_elapsed) / len(valid_elapsed), 3) if valid_elapsed else None,
        "runs": runs,
    }


def update_config_with_benchmark(model_name, result, config_path=None):
    """
    Merges a benchmark result into llme_system_config.json under a
    `benchmarks` key, keyed by model name, without disturbing other data.
    """
    config_path = config_path or default_config_path()

    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            try:
                config = json.load(f)
            except ValueError as e:
                # Never overwrite a file we could not read: it may be someone's only copy of
                # earlier numbers, and silently replacing it loses them.
                raise ValueError(f"{config_path} is not valid JSON ({e}); fix or delete it and retry") from None
        if not isinstance(config, dict):
            raise ValueError(f"{config_path} does not hold a JSON object; fix or delete it and retry")

    benchmarks = config.setdefault("benchmarks", {})
    benchmarks[model_name] = result

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return config_path
