from .updater import get_registry

def get_top_local_models(system_profile):
    """
    Cross-references hardware profile to recommend models that run at conversational speed.
    """
    ram_gb = system_profile.get("ram_total_gb", 0)
    accel = system_profile.get("hardware_acceleration", "")
    
    # Base registry of local models pulled from updater
    registry_data = get_registry()
    registry = registry_data.get("local", [])
    
    capable_models = []
    
    for model in registry:
        # Constraint check: strict memory requirement for conversational speed
        if ram_gb >= model["min_ram_gb"]:
            # Boost score if hardware acceleration is present
            boost = 2 if "Apple Silicon" in accel or "NVIDIA" in accel else 0
            model["score"] = model["speed"] + model["intelligence"] + model["ease"] + boost
            capable_models.append(model)
            
    return sorted(capable_models, key=lambda x: x["score"], reverse=True)[:5]
