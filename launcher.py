from __future__ import annotations

import argparse
import ctypes
import os
import runpy
import sys
import threading
import traceback
from pathlib import Path


def _redirect_stdio() -> None:
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        log_dir = Path.home() / ".investment_agent"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(log_dir / "app.log", "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = log_file
        if sys.stderr is None:
            sys.stderr = log_file
    except Exception:
        pass


def _enable_windows_hidpi() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "InvestmentAgent.Desktop.0.30"
        )
    except Exception:
        pass


_redirect_stdio()
_enable_windows_hidpi()


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


def _start_api(port: int) -> None:
    try:
        import local_api
        local_api.run_server(port=port)
    except Exception as exc:
        print(f"[local_api] stopped: {exc}", file=sys.stderr)


def _check_updates() -> None:
    try:
        import updater
        updater.check_for_updates(timeout=3.0)
    except Exception:
        pass


def _run_self_test() -> int:
    try:
        import PySide6.QtCore  # noqa: F401
        import PySide6.QtGui  # noqa: F401
        import PySide6.QtWidgets  # noqa: F401
        import data_sources
        import env_config  # noqa: F401
        import gui_app  # noqa: F401
        import llm_providers  # noqa: F401
        import updater
        import workbench_data  # noqa: F401

        sources = data_sources.list_data_sources()
        print(
            f"SELF_TEST_OK version={updater.APP_VERSION} sources={len(sources)}"
        )
        return 0
    except Exception:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        for target in (Path.cwd() / "self_test_error.log", BASE_DIR / "self_test_error.log"):
            try:
                target.write_text(tb, encoding="utf-8")
                break
            except Exception:
                pass
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Investment Agent Desktop Launcher")
    parser.add_argument(
        "--mode",
        choices=["gui", "api", "self-test", "cli"],
        default="gui",
    )
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-browser", action="store_true")
    args, unknown = parser.parse_known_args()

    if args.mode == "self-test":
        return _run_self_test()

    if args.mode == "cli":
        sys.argv = [str(BASE_DIR / "ia_cli.py")] + unknown
        runpy.run_path(str(BASE_DIR / "ia_cli.py"), run_name="__main__")
        return 0

    if args.mode == "api":
        _start_api(args.port)
        return 0

    threading.Thread(target=_start_api, args=(args.port,), daemon=True).start()
    threading.Thread(target=_check_updates, daemon=True).start()

    import gui_app
    gui_app.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
