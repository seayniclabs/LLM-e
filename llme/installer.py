import json
import os
import platform
import shutil
import subprocess

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".llme")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def install_ollama():
    """
    Detects the OS, checks whether Ollama is already installed, and either
    automates installation (macOS via Homebrew) or prints manual instructions
    for platforms without a safe one-shot install path.
    """
    if shutil.which("ollama"):
        print("Ollama is already installed.")
        return True

    system = platform.system()

    if system == "Darwin":
        if shutil.which("brew"):
            print("Installing Ollama via Homebrew...")
            result = subprocess.run(["brew", "install", "ollama"], check=False)
            if result.returncode == 0:
                print("Ollama installed successfully.")
                return True
            print("Homebrew install failed. Download manually from https://ollama.com/download")
            return False
        print("Homebrew not found. Download Ollama manually from https://ollama.com/download")
        return False

    if system == "Linux":
        print("To install Ollama on Linux, run:")
        print("  curl -fsSL https://ollama.com/install.sh | sh")
        return False

    if system == "Windows":
        print("Download the Ollama installer for Windows from https://ollama.com/download/windows")
        return False

    print(f"Unsupported OS '{system}'. Visit https://ollama.com/download for install options.")
    return False


def pull_model(model_name):
    """
    Pulls a model into the local Ollama installation via `ollama pull <model_name>`.
    """
    if not shutil.which("ollama"):
        print("Ollama is not installed. Run install_ollama() first.")
        return False

    print(f"Pulling model '{model_name}' via Ollama...")
    result = subprocess.run(["ollama", "pull", model_name], check=False)
    if result.returncode == 0:
        print(f"Model '{model_name}' pulled successfully.")
        return True
    print(f"Failed to pull model '{model_name}'.")
    return False


def setup_cloud_provider(provider, api_key):
    """
    Persists cloud provider configuration (provider name + API key) to
    ~/.llme/config.json so other llme commands can reuse it.
    """
    if not provider:
        print("No provider specified; skipping cloud provider setup.")
        return None

    os.makedirs(CONFIG_DIR, exist_ok=True)

    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                config = {}

    providers = config.setdefault("providers", {})
    providers[provider] = {"api_key": api_key}

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    # Restrict permissions since the file may contain an API key.
    os.chmod(CONFIG_FILE, 0o600)

    print(f"Saved configuration for provider '{provider}' to {CONFIG_FILE}")
    return CONFIG_FILE
