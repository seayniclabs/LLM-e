from .updater import get_registry

def get_top_local_models(system_profile):
    """
    Cross-references hardware profile to recommend models that run at conversational speed.
    Filters and scores using both system RAM and GPU VRAM / acceleration type, since a
    model that fits in RAM may still be too slow without adequate VRAM or GPU offload.
    """
    ram_gb = system_profile.get("ram_total_gb", 0)
    vram_gb = system_profile.get("vram_gb") or 0
    accel = system_profile.get("hardware_acceleration", "") or ""

    has_gpu_accel = any(k in accel for k in ("Apple Silicon", "NVIDIA", "AMD ROCm"))
    # Effective usable memory for model weights: unified memory (Apple Silicon) already
    # counts RAM as VRAM, so avoid double-counting; discrete GPUs add their VRAM on top.
    if "Apple Silicon" in accel:
        effective_gb = ram_gb
    else:
        effective_gb = ram_gb + vram_gb

    # Base registry of local models pulled from updater
    registry_data = get_registry()
    registry = registry_data.get("local", [])

    capable_models = []

    for model in registry:
        # Constraint check: strict memory requirement for conversational speed
        if effective_gb >= model["min_ram_gb"]:
            # Boost score if hardware acceleration is present
            boost = 2 if has_gpu_accel else 0
            # Extra boost when a discrete GPU has enough VRAM to hold the model entirely
            if vram_gb and vram_gb >= model["min_ram_gb"]:
                boost += 1
            model["score"] = model["speed"] + model["intelligence"] + model["ease"] + boost
            capable_models.append(model)

    return sorted(capable_models, key=lambda x: x["score"], reverse=True)[:5]
