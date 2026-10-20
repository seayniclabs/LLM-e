import sys
import re
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


def setup_cloud_provider(provider):
    """
    Records a cloud provider in ~/.llme/config.json by Keychain reference only. The key itself never touches a file,
    a log or the command line (the LLM-e contract): it goes into the macOS Keychain under the provider namespace that
    host apps check (com.seaynic.llme.provider.<id>), and `security` prompts for it without echo.
    """
    if not provider:
        print("No provider specified; skipping cloud provider setup.")
        return None
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", provider):
        print(f"Provider id must be lowercase letters, digits and dashes: {provider!r}")
        return None

    key_ref = {"service": f"com.seaynic.llme.provider.{provider}", "account": "default"}
    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                config = {}
    providers = config.setdefault("providers", {})
    providers[provider] = {"key_ref": key_ref}          # replaces any old entry, including a plaintext api_key from earlier versions
    fd = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_FILE, 0o600)
    print(f"Saved the Keychain reference for provider '{provider}' to {CONFIG_FILE}")

    cmd = ["security", "add-generic-password", "-U", "-s", key_ref["service"], "-a", key_ref["account"], "-w"]
    if sys.stdin.isatty():
        print("Paste the API key when asked (it is not shown and is stored only in your Keychain).")
        subprocess.run(cmd, check=False)          # -w with no value: security prompts for the key itself
    else:
        print("Store the key in your Keychain by running (it will prompt for the key):\n  " + " ".join(cmd))
    return CONFIG_FILE
