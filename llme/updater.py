import os
import json
import time
import urllib.request
import logging

REGISTRY_URL = "https://raw.githubusercontent.com/seayniclabs/llm-me/main/llme/registry.json"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "registry.json")
CACHE_EXPIRY_SECONDS = 7 * 24 * 60 * 60  # 7 days
MAX_BYTES = 2 * 1024 * 1024
# Pre-Phase-1 registry (fields min_ram_gb, speed, intelligence, ease). The Phase-1 signed registry is
# schemas/model-registry.schema.json; wiring the two together is Phase 2.


def _plausible(data):
    """The shape this module and discovery_local.py read. Anything else is refused and the last good cache is kept."""
    return isinstance(data, dict) and all(isinstance(data.get(k), list) for k in ("cloud", "local")) and \
        all(isinstance(m, dict) for k in ("cloud", "local") for m in data[k])

def get_registry():
    """
    Fetches the latest model registry from the remote URL if the local cache is
    older than 7 days or missing. Otherwise, loads from the local cache.
    Provides persistent resolution of self-correcting best practices.
    """
    needs_update = False
    
    if not os.path.exists(CACHE_FILE):
        needs_update = True
    else:
        # Check if cache is older than 7 days
        file_age = time.time() - os.path.getmtime(CACHE_FILE)
        if file_age > CACHE_EXPIRY_SECONDS:
            needs_update = True

    if needs_update:
        try:
            req = urllib.request.Request(REGISTRY_URL, headers={'User-Agent': 'LLM+Me-Updater'})
            with urllib.request.urlopen(req, timeout=5) as response:
                body = response.read(MAX_BYTES + 1) if response.status == 200 else b""
                data = json.loads(body.decode('utf-8')) if body and len(body) <= MAX_BYTES else None
                if _plausible(data):
                    tmp = CACHE_FILE + ".tmp"
                    with open(tmp, 'w') as f:
                        json.dump(data, f, indent=4)
                    os.replace(tmp, CACHE_FILE)          # never leave a half-written cache
                else:
                    logging.warning("Remote registry was missing, too large or the wrong shape; keeping the local cache.")
        except Exception as e:
            logging.warning(f"Could not fetch remote registry: {e}. Falling back to local cache.")
    
    # Load from local cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
            
    # Fallback if both remote and local fail
    return {"cloud": [], "local": []}
