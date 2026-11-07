"""What is already running on this machine: parsed answers, not model opinions."""

import http.server
import json
import threading

import pytest

from llme import inventory


@pytest.fixture
def server():
    """A real HTTP server on an ephemeral port, so the socket path is exercised too."""
    started = {}

    def start(handler):
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started["httpd"] = httpd
        return httpd.server_address[1]

    yield start
    httpd = started.get("httpd")
    if httpd is not None:
        httpd.shutdown()


def _handler(status, body, content_type="application/json"):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            payload = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    return Handler


def ollama_entry(port):
    return {"server": "Ollama", "port": port, "path": "/api/tags", "format": "ollama"}


def openai_entry(port, name="LM Studio"):
    return {"server": name, "port": port, "path": "/v1/models", "format": "openai"}


# --- payload shapes ---------------------------------------------------------

def test_ollama_models_carry_names_and_sizes():
    payload = {"models": [{"name": "llama3:8b", "size": 4700000000}, {"name": "qwen3:4b", "size": 2600000000}]}
    assert inventory._models_from_payload(payload, "ollama") == [
        {"name": "llama3:8b", "size_gb": 4.7},
        {"name": "qwen3:4b", "size_gb": 2.6},
    ]


def test_openai_models_use_the_id_field():
    payload = {"data": [{"id": "qwen2.5-7b-instruct"}, {"id": "llama-3.2-3b-instruct"}]}
    assert [m["name"] for m in inventory._models_from_payload(payload, "openai")] == [
        "qwen2.5-7b-instruct", "llama-3.2-3b-instruct",
    ]


def test_payload_without_a_model_list_is_not_a_model_list():
    assert inventory._models_from_payload({"error": "not loaded"}, "ollama") is None
    assert inventory._models_from_payload(["llama3"], "openai") is None


def test_entries_without_a_usable_name_are_skipped():
    payload = {"models": [{"name": ""}, {"size": 1}, {"name": None, "model": "phi3:mini"}]}
    assert [m["name"] for m in inventory._models_from_payload(payload, "ollama")] == ["phi3:mini"]


def test_a_zero_or_missing_size_is_left_out():
    payload = {"models": [{"name": "a", "size": 0}, {"name": "b"}]}
    assert inventory._models_from_payload(payload, "ollama") == [{"name": "a"}, {"name": "b"}]


# --- probing ----------------------------------------------------------------

def test_ollama_answers_end_to_end(server):
    port = server(_handler(200, {"models": [{"name": "llama3:8b", "size": 4700000000}]}))
    found = inventory.probe_server(ollama_entry(port))
    assert found["server"] == "Ollama"
    assert found["url"] == f"http://127.0.0.1:{port}/api/tags"
    assert found["model_count"] == 1
    assert found["models"] == [{"name": "llama3:8b", "size_gb": 4.7}]


def test_openai_style_end_to_end(server):
    port = server(_handler(200, {"object": "list", "data": [{"id": "local-model"}]}))
    found = inventory.probe_server(openai_entry(port))
    assert [m["name"] for m in found["models"]] == ["local-model"]


def test_a_closed_port_is_not_a_server(server):
    # Bind and immediately free a port: nothing listens there now.
    probe = inventory.probe_server({"server": "LM Studio", "port": 9, "path": "/v1/models", "format": "openai"},
                                  timeout=0.2)
    assert probe is None


def test_a_server_that_refuses_its_model_list_still_counts(server):
    port = server(_handler(404, b"no such endpoint"))
    found = inventory.probe_server(openai_entry(port))
    assert found["model_count"] == 0 and found["models"] == []


def test_a_login_page_instead_of_json_does_not_crash(server):
    port = server(_handler(200, b"<html>sign in</html>", content_type="text/html"))
    found = inventory.probe_server(openai_entry(port))
    assert found["models"] == [] and found["model_count"] == 0


def test_installed_keeps_the_server_order_and_skips_silent_ports(server):
    busier = server(_handler(200, {"models": [{"name": "llama3:8b"}]}))
    servers = (
        {"server": "Silent", "port": 9, "path": "/v1/models", "format": "openai"},
        ollama_entry(busier),
    )
    installed = inventory.get_installed_models(timeout=0.2, servers=servers)
    assert [entry["server"] for entry in installed] == ["Ollama"]


def test_describe_names_the_models_and_their_sizes():
    line = inventory.describe({"server": "Ollama", "url": "http://127.0.0.1:11434/api/tags",
                               "models": [{"name": "llama3:8b", "size_gb": 4.7}, {"name": "qwen3:4b"}],
                               "model_count": 2})
    assert line == "Ollama at http://127.0.0.1:11434/api/tags: llama3:8b (4.7 GB), qwen3:4b"


def test_describe_says_when_a_server_holds_nothing():
    line = inventory.describe({"server": "vLLM", "url": "http://127.0.0.1:8000/v1/models",
                               "models": [], "model_count": 0})
    assert "running, holding no models" in line
