import platform
import psutil
import json

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
    
    # Simple NPU/GPU detection fallback based on architecture
    if profile["os"] == "Darwin" and "arm" in profile["arch"].lower():
        profile["hardware_acceleration"] = "Apple Silicon (Metal/NPU)"
    else:
        profile["hardware_acceleration"] = "Unknown / Standard CPU"
        # We would add pynvml / GPUtil here for NVIDIA detection if installed
        
    return profile

if __name__ == "__main__":
    print(json.dumps(get_system_profile(), indent=2))
