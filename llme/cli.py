import sys
from llme.scanner import get_system_profile
from llme.discovery_cloud import get_top_cloud_models
from llme.discovery_local import get_top_local_models
from llme.instructions import generate_outputs

def main():
    print("Initializing LLM+Me Scanner...")
    
    # Phase 1: Hardware Scan
    print("Scanning local hardware...")
    profile = get_system_profile()
    
    # Phase 2: Cloud Model Discovery
    print("Discovering top cloud models...")
    cloud_models = get_top_cloud_models()
    
    # Phase 3: Local Model Discovery
    print("Discovering compatible local models for conversational speed...")
    local_models = get_top_local_models(profile)
    
    # Phase 4: Output Generation
    print("Generating HTML report and JSON system config...")
    html_path, json_path = generate_outputs(profile, cloud_models, local_models)
    
    print(f"\nSuccess! Reports generated:")
    print(f"- Human readable: {html_path}")
    print(f"- System config:  {json_path}")

if __name__ == "__main__":
    main()
