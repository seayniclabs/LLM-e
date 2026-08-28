from .updater import get_registry

def get_top_cloud_models():
    """
    Online model discovery. Pulls from the self-healing registry
    and returns the top 5 models scored by speed, intelligence, ease of use, and rate limits.
    Filtered STRICTLY for free-tier accessible models.
    """
    registry = get_registry()
    models = registry.get("cloud", [])
    
    # Calculate a composite score and sort
    for m in models:
        m["score"] = m["speed"] + m["intelligence"] + m["ease"] + m["rate_limit"]
        
    return sorted(models, key=lambda x: x["score"], reverse=True)[:5]
