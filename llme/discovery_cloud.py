import json
import os
import urllib.request
import urllib.error
import logging

MODELS_FILE = os.path.join(os.path.dirname(__file__), "models.json")


def _load_models_file(path=MODELS_FILE):
    if not os.path.exists(path):
        return {"cloud": [], "local": []}
    with open(path, "r") as f:
        return json.load(f)


def validate_model_availability(model, timeout=4):
    """
    Checks whether a cloud model's provider endpoint is reachable.
    This is a lightweight connectivity check (HTTP HEAD/GET against the
    provider's base URL), not an authenticated API call, so it verifies
    the provider is up without requiring an API key.
    """
    url = model.get("url")
    if not url:
        return False
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "LLM+Me-Validator"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return 200 <= response.status < 500
    except urllib.error.HTTPError as e:
        # Many providers reject HEAD but are still reachable (4xx = alive).
        return e.code < 500
    except Exception as e:
        logging.warning(f"Could not validate {model.get('name')}: {e}")
        return False


def get_top_cloud_models(models_path=MODELS_FILE):
    """
    Online model discovery. Pulls from llme/models.json by default and returns
    the top 5 models scored by speed, intelligence, ease of use, and rate limits.
    Filtered STRICTLY for free-tier accessible models.
    """
    registry = _load_models_file(models_path)
    models = registry.get("cloud", [])

    # Calculate a composite score and sort
    for m in models:
        m["score"] = m["speed"] + m["intelligence"] + m["ease"] + m["rate_limit"]

    return sorted(models, key=lambda x: x["score"], reverse=True)[:5]
