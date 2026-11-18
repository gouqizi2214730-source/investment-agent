from __future__ import annotations

import argparse
import os
import runpy
import sys
import threading
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _setup_paths() -> Path:
    base = _base_dir()
    candidates = [str(base), str(base / "scripts")]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.extend([str(meipass), str(Path(meipass) / "scripts")])
    for p in candidates:
        if p and p not in sys.path:
            sys.path.insert(0, p)
    existing = os.environ.get("PYTHONPATH", "")
    parts = [p for p in candidates if p] + ([existing] if existing else [])
    os.environ["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(parts))
    return base


BASE_DIR = _setup_paths()

if False:
    import app, workbench_data, ia_cli, gui_app, env_config, llm_providers, updater  # noqa: F401

from llm_providers import load_llm_config, start_local_api_server
from updater import check_for_updates


def _check_updates() -> None:
    try:
        info = check_for_updates()
        if info.get("has_update"):
            print(f"[Updater] New version available: {info.get('latest_version')} (current: {info.get('current_version')}) -> {info.get('release_url')}")
        else:
            print(f"[Updater] Up to date ({info.get('current_version')}).")
    except Exception as exc:
        print(f"[Updater] Update check skipped: {exc}")


def _start_api(host: str, port: int) -> None:
    print(f"[LLM API] Local OpenAI-compatible server listening on http://{host}:{port}")
    start_local_api_server(host=host, port=port)


def _run_self_test() -> int:
    modules = ["app", "workbench_data", "ia_cli", "gui_app", "env_config", "llm_providers", "updater", "view_verifier", "view_store", "view_plausibility", "research_map", "research_archive"]
    for mod in modules:
        __import__(mod)
        print(f"[Self-Test] OK: {mod}")
    print("[Self-Test] All modules imported successfully.")
    import workbench_data as wd
    snap, _ = wd.latest_snapshot()
    assert snap is None or isinstance(snap, dict)
    assert isinstance(wd.transmission_edges(), dict)
    assert isinstance(wd.views_matrix(), dict)
    assert isinstance(wd.research_archive_rows(), list)
    print("[Self-Test] workbench_data checks OK.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Investment Agent 全球宏观投研工作台启动器")
    parser.add_argument("--mode", choices=["gui", "workbench", "cli", "api", "self-test"], default="gui")
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=8787)
    parser.add_argument("--no-api", action="store_true")
    parser.add_argument("--no-update-check", action="store_true")
    args, extra = parser.parse_known_args()

    if args.mode == "self-test":
        return _run_self_test()

    if not args.no_update_check:
        threading.Thread(target=_check_updates, daemon=True).start()

    if args.mode == "api":
        _start_api(args.api_host, args.api_port)
        return 0

    if not args.no_api:
        cfg = load_llm_config()
        if cfg.get("local_api_enabled", True):
            threading.Thread(target=_start_api, args=(args.api_host, args.api_port), daemon=True).start()

    if args.mode == "gui":
        import gui_app
        gui_app.main()
        return 0

    if args.mode == "cli":
        cli_path = BASE_DIR / "ia_cli.py"
        sys.argv = [str(cli_path), *extra]
        runpy.run_path(str(cli_path), run_name="__main__")
        return 0

    from streamlit.web import cli as stcli
    app_path = BASE_DIR / "app.py"
    sys.argv = ["streamlit", "run", str(app_path), "--global.developmentMode=false", *extra]
    return int(stcli.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
from updater import check_for_updates


def _base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _check_updates() -> None:
    try:
        info = check_for_updates()
        if info.get("has_update"):
            print(
                f"[Updater] New version available: {info.get('latest_version')} "
                f"(current: {info.get('current_version')}) -> {info.get('release_url')}"
            )
        else:
            print(f"[Updater] Up to date ({info.get('current_version')}).")
    except Exception as exc:
        print(f"[Updater] Update check skipped: {exc}")


def _start_api(host: str, port: int) -> None:
    cfg = load_llm_config()
    server = start_local_api_server(host=host, port=port, config=cfg)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[LLM API] Local server listening on http://{host}:{port}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Investment Agent Launcher")
    parser.add_argument(
        "--mode",
        choices=("workbench", "cli", "api"),
        default="workbench",
        help="Launch Streamlit workbench, CLI, or API-only mode",
    )
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=8787)
    parser.add_argument("--no-update-check", action="store_true")
    parser.add_argument("--no-api", action="store_true")
    args, remaining = parser.parse_known_args(argv)

    base = _base_dir()
    os.chdir(base)
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    if not args.no_update_check:
        _check_updates()

    if not args.no_api:
        _start_api(args.api_host, args.api_port)

    if args.mode == "api":
        threading.Event().wait()
        return 0

    if args.mode == "cli":
        cli_path = base / "ia_cli.py"
        sys.argv = [str(cli_path), *remaining]
        runpy.run_path(str(cli_path), run_name="__main__")
        return 0

    from streamlit.web import cli as stcli

    app_path = base / "app.py"
    sys.argv = ["streamlit", "run", str(app_path), "--global.developmentMode=false", *remaining]
    return int(stcli.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
