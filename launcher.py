from __future__ import annotations

import argparse
import os
import runpy
import sys
import threading
from pathlib import Path

from llm_providers import load_llm_config, start_local_api_server
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
