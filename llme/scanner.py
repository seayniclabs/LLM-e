import platform
import psutil
import json

from llme.gpu_scanner import get_gpu_profile

def get_system_profile():
    """
    Scans the local hardware and returns a standardized JSON profile.
    Cross-platform support for macOS, Linux, and Windows.
    """
    profile = {
        "os": platform.system(),
        "release": platform.release(),
        "arch": platform.machine(),
        "cpu_cores_physical": psutil.cpu_count(logical=False),
        "cpu_cores_logical": psutil.cpu_count(logical=True),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
    }

    gpu_profile = get_gpu_profile()
    profile["gpu_type"] = gpu_profile["gpu_type"]
    profile["vram_gb"] = gpu_profile["vram_gb"]
    profile["hardware_acceleration"] = gpu_profile["hardware_acceleration"]
    profile["driver_version"] = gpu_profile["driver_version"]

    return profile

if __name__ == "__main__":
    print(json.dumps(get_system_profile(), indent=2))
