import argparse
import json
import sys

from llme.scanner import get_system_profile
from llme.discovery_cloud import get_top_cloud_models, validate_model_availability, MODELS_FILE, _load_models_file
from llme.discovery_local import get_top_local_models
from llme.instructions import generate_outputs


def run_scan():
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


def run_update_models(args):
    print(f"Validating cloud models in {MODELS_FILE}...")
    registry = _load_models_file()
    cloud_models = registry.get("cloud", [])

    if not cloud_models:
        print("No cloud models found in models.json.")
        return

    results = []
    for model in cloud_models:
        available = validate_model_availability(model)
        status = "OK" if available else "UNREACHABLE"
        print(f"- {model['name']} ({model['provider']}): {status}")
        results.append({"name": model["name"], "provider": model["provider"], "available": available})

    available_count = sum(1 for r in results if r["available"])
    print(f"\n{available_count}/{len(results)} providers reachable.")
    return results


def run_install(args):
    from llme.installer import install_ollama, pull_model, setup_cloud_provider

    if args.local:
        install_ollama()
        pull_model(args.local)

    if args.cloud:
        setup_cloud_provider(args.cloud, args.api_key)

    if not args.local and not args.cloud:
        install_ollama()


def run_benchmark(args):
    from llme.benchmarker import benchmark_model, update_config_with_benchmark

    result = benchmark_model(args.model, num_runs=args.runs)
    print(json.dumps(result, indent=2))
    update_config_with_benchmark(args.model, result)


def build_parser():
    parser = argparse.ArgumentParser(prog="llme", description="Hardware scanner and AI model recommender")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("scan", help="Scan hardware and generate recommendation reports (default)")

    subparsers.add_parser("update-models", help="Validate and refresh the cloud model registry")

    install_parser = subparsers.add_parser("install", help="Install local/cloud AI providers")
    install_parser.add_argument("--local", metavar="MODEL", help="Ollama model to install and pull, e.g. llama3")
    install_parser.add_argument("--cloud", metavar="PROVIDER", help="Cloud provider to configure, e.g. openrouter")
    install_parser.add_argument("--api-key", metavar="KEY", help="API key for the cloud provider")

    benchmark_parser = subparsers.add_parser("benchmark", help="Benchmark a local model's inference performance")
    benchmark_parser.add_argument("model", help="Model name to benchmark, e.g. llama3")
    benchmark_parser.add_argument("--runs", type=int, default=3, help="Number of benchmark runs (default: 3)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "update-models":
        run_update_models(args)
    elif args.command == "install":
        run_install(args)
    elif args.command == "benchmark":
        run_benchmark(args)
    else:
        run_scan()


if __name__ == "__main__":
    main()
