"""Benchmarks: numbers from a real answer, a clear refusal for bad input, no traceback for a
server that is not Ollama."""

import http.server
import json
import threading

import pytest

from llme import benchmarker


@pytest.fixture
def ollama():
    """A stub Ollama, on a real socket, answering with whatever body the test sets."""
    state = {"body": {}, "status": 200, "raw": None}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            state["request"] = json.loads(self.rfile.read(length) or b"{}")
            payload = state["raw"] if state["raw"] is not None else json.dumps(state["body"]).encode()
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    state["url"] = f"http://127.0.0.1:{httpd.server_address[1]}/api/generate"
    yield state
    httpd.shutdown()


ANSWER = {"eval_count": 100, "eval_duration": 2_000_000_000, "prompt_eval_duration": 500_000_000}


def test_tokens_per_second_and_ttft_come_from_the_answer(ollama, monkeypatch):
    monkeypatch.setattr(benchmarker, "OLLAMA_URL", ollama["url"])
    ollama["body"] = ANSWER

    result = benchmarker._single_run("llama3:8b")

    assert result["tokens_per_second"] == 50.0          # 100 tokens over 2 s
    assert result["ttft_s"] == 0.5                      # prompt eval of 0.5 s
    assert result["eval_count"] == 100
    assert ollama["request"]["model"] == "llama3:8b"
    assert ollama["request"]["stream"] is False


def test_benchmark_averages_the_runs(ollama, monkeypatch):
    monkeypatch.setattr(benchmarker, "OLLAMA_URL", ollama["url"])
    ollama["body"] = ANSWER

    result = benchmarker.benchmark_model("llama3:8b", num_runs=3)

    assert result["status"] == "ok"
    assert result["num_runs"] == 3 and len(result["runs"]) == 3
    assert result["avg_tokens_per_second"] == 50.0
    assert result["avg_elapsed_s"] is not None


def test_an_answer_without_timings_is_still_reported(ollama, monkeypatch):
    monkeypatch.setattr(benchmarker, "OLLAMA_URL", ollama["url"])
    ollama["body"] = {"response": "no counters here"}

    result = benchmarker.benchmark_model("llama3:8b", num_runs=1)

    assert result["status"] == "ok"
    assert result["avg_tokens_per_second"] is None and result["avg_ttft_s"] is None


def test_a_page_instead_of_json_is_a_reported_failure(ollama, monkeypatch, capsys):
    # The old behaviour raised JSONDecodeError out of the middle of the benchmark.
    monkeypatch.setattr(benchmarker, "OLLAMA_URL", ollama["url"])
    ollama["raw"] = b"<html>this port is a proxy</html>"

    result = benchmarker.benchmark_model("llama3:8b", num_runs=1)

    assert result["status"] == "unavailable"
    assert "not with JSON" in result["error"]
    assert "ollama" in result["hint"]


def test_json_that_is_not_an_object_is_a_reported_failure(ollama, monkeypatch):
    monkeypatch.setattr(benchmarker, "OLLAMA_URL", ollama["url"])
    ollama["raw"] = b'["not", "a", "model"]'

    result = benchmarker.benchmark_model("llama3:8b", num_runs=1)
    assert result["status"] == "unavailable"


def test_nothing_listening_is_reported_with_a_hint(monkeypatch):
    monkeypatch.setattr(benchmarker, "OLLAMA_URL", "http://127.0.0.1:9/api/generate")
    result = benchmarker.benchmark_model("llama3:8b", num_runs=1)
    assert result["status"] == "unavailable" and result["hint"]


@pytest.mark.parametrize("runs", [0, -1, 1.5, "3", None, True])
def test_a_benchmark_needs_at_least_one_run(runs):
    with pytest.raises(ValueError, match="num_runs"):
        benchmarker.benchmark_model("llama3:8b", num_runs=runs)


def test_the_config_lands_in_the_directory_you_ran_the_command_in(tmp_path, monkeypatch):
    workdir = tmp_path / "somewhere"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    written = benchmarker.update_config_with_benchmark("llama3:8b", {"status": "ok"})

    assert written == str(workdir / "llme_system_config.json")
    assert json.loads((workdir / "llme_system_config.json").read_text())["benchmarks"]["llama3:8b"] == {"status": "ok"}


def test_merging_keeps_the_rest_of_the_config(tmp_path):
    config = tmp_path / "llme_system_config.json"
    config.write_text(json.dumps({"hardware": {"os": "Linux"}, "benchmarks": {"old": {"status": "ok"}}}))

    benchmarker.update_config_with_benchmark("new", {"status": "ok"}, config_path=str(config))

    saved = json.loads(config.read_text())
    assert saved["hardware"] == {"os": "Linux"}
    assert set(saved["benchmarks"]) == {"old", "new"}


def test_a_corrupt_config_is_named_and_left_alone(tmp_path):
    config = tmp_path / "llme_system_config.json"
    config.write_text("{not json")

    with pytest.raises(ValueError, match="llme_system_config.json"):
        benchmarker.update_config_with_benchmark("llama3:8b", {"status": "ok"}, config_path=str(config))
    assert config.read_text() == "{not json"


def test_a_config_holding_something_else_is_left_alone(tmp_path):
    config = tmp_path / "llme_system_config.json"
    config.write_text(json.dumps(["not", "a", "config"]))

    with pytest.raises(ValueError, match="JSON object"):
        benchmarker.update_config_with_benchmark("llama3:8b", {"status": "ok"}, config_path=str(config))
    assert json.loads(config.read_text()) == ["not", "a", "config"]
