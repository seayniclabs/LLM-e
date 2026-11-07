"""What AI is already on this machine.

The scan recommends models to install. This module answers the other half of that question:
which model servers are already running on localhost, and which models they hold. A report
that suggests downloading a model someone finished pulling last week is noise, and a server
that answers but holds nothing is worth saying out loud too.

Only localhost is probed, and only on the ports the common servers bind by default. Every
probe has a short timeout, and a closed port refuses immediately, so an idle machine costs
a few milliseconds.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_HOST = "127.0.0.1"
DEFAULT_TIMEOUT = 0.4  # seconds per port
MAX_BYTES = 2 * 1024 * 1024

# Ports the usual local servers bind by default. Keep this list short: each entry is one
# socket, and a port that filters instead of refusing costs the whole timeout.
KNOWN_SERVERS: Sequence[Dict[str, Any]] = (
    {"server": "Ollama", "port": 11434, "path": "/api/tags", "format": "ollama"},
    {"server": "LM Studio", "port": 1234, "path": "/v1/models", "format": "openai"},
    {"server": "vLLM", "port": 8000, "path": "/v1/models", "format": "openai"},
    {"server": "llama.cpp server", "port": 8080, "path": "/v1/models", "format": "openai"},
)


def _size_gb(size_bytes: Any) -> Optional[float]:
    """Model size in decimal GB, the same scale `ollama list` prints."""
    try:
        size = float(size_bytes)
    except (TypeError, ValueError):
        return None
    if size <= 0:
        return None
    return round(size / 1e9, 1)


def _models_from_payload(payload: Any, fmt: str) -> Optional[List[Dict[str, Any]]]:
    """Pull the model list out of a server's answer. None means the shape was not one."""
    if not isinstance(payload, dict):
        return None
    if fmt == "ollama":
        entries = payload.get("models")
    else:
        entries = payload.get("data")
    if not isinstance(entries, list):
        return None

    models: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("model") or entry.get("id")
        if not isinstance(name, str) or not name.strip():
            continue
        model: Dict[str, Any] = {"name": name.strip()}
        size_gb = _size_gb(entry.get("size"))
        if size_gb is not None:
            model["size_gb"] = size_gb
        models.append(model)
    return models


def probe_server(entry: Dict[str, Any], host: str = DEFAULT_HOST,
                 timeout: float = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """Ask one server for its model list. None means nothing answered on that port."""
    url = "http://{host}:{port}{path}".format(host=host, port=entry["port"], path=entry["path"])
    request = urllib.request.Request(url, headers={"User-Agent": "LLM+Me-Inventory"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            body = response.read(MAX_BYTES)
    except urllib.error.HTTPError:
        # Something is listening but will not hand out its model list: still worth showing.
        return {"server": entry["server"], "url": url, "models": [], "model_count": 0}
    except (urllib.error.URLError, OSError, ValueError):
        return None

    try:
        payload = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        return {"server": entry["server"], "url": url, "models": [], "model_count": 0}

    models = _models_from_payload(payload, entry.get("format", "openai"))
    if models is None:
        models = []
    return {"server": entry["server"], "url": url, "models": models, "model_count": len(models)}


def get_installed_models(host: str = DEFAULT_HOST, timeout: float = DEFAULT_TIMEOUT,
                         servers: Sequence[Dict[str, Any]] = KNOWN_SERVERS) -> List[Dict[str, Any]]:
    """Every known local server that answers, in the order the servers are listed."""
    installed: List[Dict[str, Any]] = []
    for entry in servers:
        found = probe_server(entry, host=host, timeout=timeout)
        if found is not None:
            installed.append(found)
    return installed


def describe(entry: Dict[str, Any]) -> str:
    """One line for the terminal: the server, its address, and what it holds."""
    names = []
    for model in entry.get("models", []):
        size = model.get("size_gb")
        names.append(f"{model['name']} ({size} GB)" if size else model["name"])
    if not names:
        return "{server} at {url} (running, holding no models)".format(**entry)
    return "{server} at {url}: {names}".format(names=", ".join(names), **entry)
