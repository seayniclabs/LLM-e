import platform
import re
import subprocess


def _run(cmd):
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=5, check=False
        ).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""


def _detect_apple_silicon():
    brand = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    mem_bytes = _run(["sysctl", "-n", "hw.memsize"])
    vram_gb = None
    if mem_bytes.isdigit():
        # Apple Silicon uses unified memory; treat total RAM as accessible VRAM.
        vram_gb = round(int(mem_bytes) / (1024**3), 2)
    return {
        "gpu_type": "Apple Silicon",
        "vram_gb": vram_gb,
        "hardware_acceleration": f"Apple Silicon (Metal/NPU) - {brand}" if brand else "Apple Silicon (Metal/NPU)",
        "driver_version": platform.mac_ver()[0] or None,
    }


def _detect_nvidia():
    output = _run([
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader",
    ])
    if not output:
        return None
    first_line = output.splitlines()[0]
    parts = [p.strip() for p in first_line.split(",")]
    if len(parts) < 3:
        return None
    name, mem_str, driver = parts[0], parts[1], parts[2]
    mem_match = re.search(r"([\d.]+)", mem_str)
    vram_gb = round(float(mem_match.group(1)) / 1024, 2) if mem_match else None
    return {
        "gpu_type": f"NVIDIA ({name})",
        "vram_gb": vram_gb,
        "hardware_acceleration": "NVIDIA CUDA",
        "driver_version": driver,
    }


def _detect_amd():
    output = _run(["rocm-smi", "--showproductname", "--showmeminfo", "vram"])
    if not output:
        return None
    driver = _run(["rocm-smi", "--showdriverversion"])
    vram_gb = None
    mem_match = re.search(r"([\d]+)\s*MB", output)
    if mem_match:
        vram_gb = round(int(mem_match.group(1)) / 1024, 2)
    return {
        "gpu_type": "AMD ROCm",
        "vram_gb": vram_gb,
        "hardware_acceleration": "AMD ROCm",
        "driver_version": driver or None,
    }


def get_gpu_profile():
    """
    Detects available GPU/NPU hardware acceleration across platforms.
    Checks Apple Silicon Metal/NPU, NVIDIA CUDA, and AMD ROCm, in that
    order of platform likelihood, falling back to standard CPU.
    """
    if platform.system() == "Darwin" and "arm" in platform.machine().lower():
        return _detect_apple_silicon()

    nvidia = _detect_nvidia()
    if nvidia:
        return nvidia

    amd = _detect_amd()
    if amd:
        return amd

    return {
        "gpu_type": "None",
        "vram_gb": None,
        "hardware_acceleration": "Unknown / Standard CPU",
        "driver_version": None,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_gpu_profile(), indent=2))
