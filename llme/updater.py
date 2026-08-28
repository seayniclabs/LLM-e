import os
import json
import time
import urllib.request
import logging

REGISTRY_URL = "https://raw.githubusercontent.com/seayniclabs/llm-me/main/llme/registry.json"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "registry.json")
CACHE_EXPIRY_SECONDS = 7 * 24 * 60 * 60  # 7 days

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
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    with open(CACHE_FILE, 'w') as f:
                        json.dump(data, f, indent=4)
        except Exception as e:
            logging.warning(f"Could not fetch remote registry: {e}. Falling back to local cache.")
    
    # Load from local cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
            
    # Fallback if both remote and local fail
    return {"cloud": [], "local": []}
