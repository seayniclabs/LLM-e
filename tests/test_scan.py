"""The scan and the CLI: what a scan reports, and what it refuses to do."""

import json

import pytest

from llme import cli, instructions

PROFILE = {"os": "Linux", "arch": "x86_64", "ram_total_gb": 32.0, "ram_available_gb": 24.0,
           "gpu_type": "None", "vram_gb": None, "hardware_acceleration": "Unknown / Standard CPU"}


def installed_entry():
    return {"server": "Ollama", "url": "http://127.0.0.1:11434/api/tags",
            "models": [{"name": "llama3:8b", "size_gb": 4.7}], "model_count": 1}


@pytest.fixture
def scan_env(monkeypatch):
    monkeypatch.setattr(cli, "get_system_profile", lambda: dict(PROFILE))
    monkeypatch.setattr(cli, "get_top_cloud_models", lambda: [])
    monkeypatch.setattr(cli, "get_top_local_models", lambda profile: [])


def test_a_scan_records_what_is_already_installed(tmp_path, scan_env, monkeypatch, capsys):
    monkeypatch.setattr(cli.inventory, "get_installed_models", lambda **kwargs: [installed_entry()])

    html_path, json_path = cli.run_scan(output_dir=str(tmp_path))

    report = json.loads((tmp_path / "llme_system_config.json").read_text())
    assert report["installed"] == [installed_entry()]
    assert "Ollama" in (tmp_path / "llme_report.html").read_text()
    assert "llama3:8b" in (tmp_path / "llme_report.html").read_text()
    assert "Ollama at http://127.0.0.1:11434/api/tags: llama3:8b (4.7 GB)" in capsys.readouterr().out


def test_a_scan_says_so_when_nothing_is_running(tmp_path, scan_env, monkeypatch, capsys):
    monkeypatch.setattr(cli.inventory, "get_installed_models", lambda **kwargs: [])

    cli.run_scan(output_dir=str(tmp_path))

    out = capsys.readouterr().out
    assert "nothing answered on Ollama (11434)" in out
    html = (tmp_path / "llme_report.html").read_text()
    assert "Nothing answered on the local AI ports (Ollama 11434" in html
    assert json.loads((tmp_path / "llme_system_config.json").read_text())["installed"] == []


def test_scan_no_probe_touches_no_sockets(tmp_path, scan_env, monkeypatch):
    def explode(**kwargs):
        raise AssertionError("--no-probe must not probe")

    monkeypatch.setattr(cli.inventory, "get_installed_models", explode)
    monkeypatch.chdir(tmp_path)

    cli.main(["scan", "--no-probe"])

    assert json.loads((tmp_path / "llme_system_config.json").read_text())["installed"] == []


def test_no_subcommand_runs_a_scan(tmp_path, scan_env, monkeypatch):
    monkeypatch.setattr(cli.inventory, "get_installed_models", lambda **kwargs: [])
    monkeypatch.chdir(tmp_path)

    cli.main([])

    assert (tmp_path / "llme_report.html").exists()


def test_inventory_prints_json(monkeypatch, capsys):
    monkeypatch.setattr(cli.inventory, "get_installed_models", lambda **kwargs: [installed_entry()])

    cli.main(["inventory", "--json"])

    printed = capsys.readouterr().out
    assert json.loads(printed) == [installed_entry()]


def test_inventory_prints_one_line_per_server(monkeypatch, capsys):
    monkeypatch.setattr(cli.inventory, "get_installed_models", lambda **kwargs: [installed_entry()])

    cli.main(["inventory"])

    assert capsys.readouterr().out.strip() == (
        "Ollama at http://127.0.0.1:11434/api/tags: llama3:8b (4.7 GB)")


def test_inventory_says_what_it_checked_when_nothing_answers(monkeypatch, capsys):
    monkeypatch.setattr(cli.inventory, "get_installed_models", lambda **kwargs: [])

    cli.main(["inventory"])

    out = capsys.readouterr().out
    assert "No AI server answered on 127.0.0.1" in out
    assert "vLLM (8000)" in out


def test_benchmark_refuses_zero_runs_before_doing_any_work(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["benchmark", "llama3", "--runs", "0"])

    assert exit_info.value.code == 2
    assert "needs at least one run" in capsys.readouterr().err


def test_benchmark_accepts_a_positive_run_count():
    parser = cli.build_parser()
    assert parser.parse_args(["benchmark", "llama3", "--runs", "5"]).runs == 5
    assert parser.parse_args(["benchmark", "llama3"]).runs == 3


def test_generate_outputs_keeps_existing_benchmarks(tmp_path):
    json_path = tmp_path / "llme_system_config.json"
    json_path.write_text(json.dumps({"benchmarks": {"llama3:8b": {"status": "ok"}}}))

    instructions.generate_outputs(dict(PROFILE), [], [], output_dir=str(tmp_path))

    assert json.loads(json_path.read_text())["benchmarks"] == {"llama3:8b": {"status": "ok"}}
