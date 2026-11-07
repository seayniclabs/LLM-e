import argparse
import json
import sys

from llme import inventory
from llme.scanner import get_system_profile
from llme.discovery_cloud import get_top_cloud_models, validate_model_availability, MODELS_FILE, _load_models_file
from llme.discovery_local import get_top_local_models
from llme.instructions import generate_outputs


def _positive_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a whole number") from None
    if number < 1:
        raise argparse.ArgumentTypeError(f"needs at least one run, got {number}")
    return number


def _positive_timeout(value):
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number of seconds") from None
    if seconds <= 0:
        raise argparse.ArgumentTypeError(f"timeout must be greater than zero, got {seconds}")
    return seconds


def run_scan(probe_servers=True, output_dir="."):
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

    # Phase 4: What is already serving on this machine
    installed = []
    if probe_servers:
        print("Checking for AI servers already running here...")
        installed = inventory.get_installed_models()
        if installed:
            for entry in installed:
                print(f"- {inventory.describe(entry)}")
        else:
            print("- nothing answered on " + ", ".join(
                f"{entry['server']} ({entry['port']})" for entry in inventory.KNOWN_SERVERS))

    # Phase 5: Output Generation
    print("Generating HTML report and JSON system config...")
    html_path, json_path = generate_outputs(
        profile, cloud_models, local_models, output_dir=output_dir, installed=installed
    )

    print(f"\nSuccess! Reports generated:")
    print(f"- Human readable: {html_path}")
    print(f"- System config:  {json_path}")
    return html_path, json_path


def run_inventory(args):
    installed = inventory.get_installed_models(host=args.host, timeout=args.timeout)
    if args.json:
        print(json.dumps(installed, indent=2))
        return installed

    if not installed:
        print("No AI server answered on {host}. Checked {servers}.".format(
            host=args.host,
            servers=", ".join(f"{e['server']} ({e['port']})" for e in inventory.KNOWN_SERVERS)))
        return installed

    for entry in installed:
        print(inventory.describe(entry))
    return installed


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
        setup_cloud_provider(args.cloud)

    if not args.local and not args.cloud:
        install_ollama()


def run_benchmark(args):
    from llme.benchmarker import benchmark_model, update_config_with_benchmark

    try:
        result = benchmark_model(args.model, num_runs=args.runs)
    except ValueError as err:
        print(f"llme benchmark: {err}", file=sys.stderr)
        return None
    print(json.dumps(result, indent=2))
    update_config_with_benchmark(args.model, result)
    return result


def build_parser():
    parser = argparse.ArgumentParser(prog="llme", description="Hardware scanner and AI model recommender")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan hardware and generate recommendation reports (default)")
    scan_parser.add_argument("--no-probe", action="store_true",
                             help="Do not look for model servers already running on this machine")

    subparsers.add_parser("update-models", help="Validate and refresh the cloud model registry")

    inventory_parser = subparsers.add_parser("inventory", help="List the model servers already running here")
    inventory_parser.add_argument("--json", action="store_true", help="Print the inventory as JSON")
    inventory_parser.add_argument("--host", default=inventory.DEFAULT_HOST, help="Host to probe (default: 127.0.0.1)")
    inventory_parser.add_argument("--timeout", type=_positive_timeout, default=inventory.DEFAULT_TIMEOUT,
                                  metavar="SECONDS", help="Seconds to wait per port (default: %(default)s)")

    install_parser = subparsers.add_parser("install", help="Install local/cloud AI providers")
    install_parser.add_argument("--local", metavar="MODEL", help="Ollama model to install and pull, e.g. llama3")
    install_parser.add_argument("--cloud", metavar="PROVIDER", help="Cloud provider to configure, e.g. openrouter")

    benchmark_parser = subparsers.add_parser("benchmark", help="Benchmark a local model's inference performance")
    benchmark_parser.add_argument("model", help="Model name to benchmark, e.g. llama3")
    benchmark_parser.add_argument("--runs", type=_positive_int, default=3, metavar="N",
                                  help="Number of benchmark runs, at least 1 (default: 3)")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "update-models":
        run_update_models(args)
    elif args.command == "install":
        run_install(args)
    elif args.command == "benchmark":
        run_benchmark(args)
    elif args.command == "inventory":
        run_inventory(args)
    elif args.command == "scan":
        run_scan(probe_servers=not args.no_probe)
    else:
        run_scan()


if __name__ == "__main__":
    main()
