"""The model registry: fetched when the local copy is older than a week, otherwise read from cache.

The cache belongs to the user, not to the installation: a wheel lives in site-packages, which is
often root-owned and read-only, and a cache kept there survives neither an upgrade nor a non-root
run. It goes under the platform's cache directory instead. A cache left inside the package
directory by an earlier version is copied across on first use, keeping its age, so the weekly
refresh clock stays honest.
"""

import os
import json
import platform
import shutil
import time
import urllib.request
import logging

REPOSITORY = "seayniclabs/LLM-e"
REGISTRY_URL = f"https://raw.githubusercontent.com/{REPOSITORY}/main/llme/registry.json"
CACHE_FILENAME = "registry.json"
# Where versions before the per-user cache wrote it: inside the package, i.e. site-packages.
LEGACY_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_FILENAME)
CACHE_EXPIRY_SECONDS = 7 * 24 * 60 * 60  # 7 days
MAX_BYTES = 2 * 1024 * 1024
# Pre-Phase-1 registry (fields min_ram_gb, speed, intelligence, ease). The Phase-1 signed registry is
# schemas/model-registry.schema.json; wiring the two together is Phase 2.


def cache_dir():
    """The per-user cache directory, honouring LLME_CACHE_DIR and XDG_CACHE_HOME."""
    override = os.environ.get("LLME_CACHE_DIR")
    if override:
        return override
    home = os.path.expanduser("~")
    system = platform.system()
    if system == "Darwin":
        return os.path.join(home, "Library", "Caches", "llme")
    if system == "Windows":
        return os.path.join(os.environ.get("LOCALAPPDATA") or home, "llme", "cache")
    return os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(home, ".cache"), "llme")


CACHE_FILE = os.path.join(cache_dir(), CACHE_FILENAME)


def _plausible(data):
    """The shape this module and discovery_local.py read. Anything else is refused and the last good cache is kept."""
    return isinstance(data, dict) and all(isinstance(data.get(k), list) for k in ("cloud", "local")) and \
        all(isinstance(m, dict) for k in ("cloud", "local") for m in data[k])


def _migrate_legacy_cache():
    """Copy a package-local cache written by an earlier version, keeping its age."""
    if os.path.exists(CACHE_FILE) or not os.path.exists(LEGACY_CACHE_FILE):
        return
    try:
        os.makedirs(os.path.dirname(CACHE_FILE) or ".", exist_ok=True)
        shutil.copy2(LEGACY_CACHE_FILE, CACHE_FILE)   # copy2 keeps the mtime, so an old copy still refreshes
    except OSError as e:
        logging.warning(f"Could not move the old registry cache to {CACHE_FILE}: {e}")


def get_registry():
    """
    Fetches the latest model registry from the remote URL if the local cache is
    older than 7 days or missing. Otherwise, loads from the local cache.
    Provides persistent resolution of self-correcting best practices.
    """
    _migrate_legacy_cache()

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
                    os.makedirs(os.path.dirname(CACHE_FILE) or ".", exist_ok=True)
                    tmp = CACHE_FILE + ".tmp"
                    with open(tmp, 'w') as f:
                        json.dump(data, f, indent=4)
                    os.replace(tmp, CACHE_FILE)          # never leave a half-written cache
                else:
                    logging.warning("Remote registry was missing, too large or the wrong shape; keeping the local cache.")
        except Exception as e:
            logging.warning(f"Could not fetch {REGISTRY_URL}: {e}. Falling back to the local cache.")
    
    # Load from local cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
            
    # Fallback if both remote and local fail
    return {"cloud": [], "local": []}
