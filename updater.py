"""Auto-update checker and upgrader against GitHub Releases and branches."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import requests

APP_VERSION = "0.31.0"
UPSTREAM_REPO = "bojing951-hash/investment-agent"
DEFAULT_REPO = os.environ.get("INVESTMENT_AGENT_UPDATE_REPO", "gouqizi2214730-source/investment-agent")
DEFAULT_BRANCH = os.environ.get("INVESTMENT_AGENT_UPDATE_BRANCH", "main")


def _gh_api(path: str) -> str:
    return f"https://{'api.github.com'}/{path.lstrip('/')}"


def parse_version(version_str: str) -> tuple[int, int, int, int, str]:
    clean = str(version_str or "").strip().lstrip("vV")
    m = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-.]?(.+))?$", clean)
    if not m:
        return (0, 0, 0, 0, clean)
    major = int(m.group(1) or 0)
    minor = int(m.group(2) or 0)
    patch = int(m.group(3) or 0)
    pre = (m.group(4) or "").strip()
    is_stable = 1 if not pre else 0
    return (major, minor, patch, is_stable, pre)


def is_newer_version(remote_version: str, current_version: str = APP_VERSION) -> bool:
    r = parse_version(remote_version)
    c = parse_version(current_version)
    if r[:4] != c[:4]:
        return r[:4] > c[:4]
    return r[4] > c[4]


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "investment-agent-updater"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def check_for_updates(
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    include_prerelease: bool = True,
    timeout: int = 15,
) -> dict[str, Any]:
    headers = _github_headers()
    release_data: dict[str, Any] | None = None
    try:
        resp = requests.get(_gh_api(f"repos/{repo}/releases/latest"), headers=headers, timeout=timeout)
        if resp.status_code == 200:
            release_data = resp.json()
    except Exception:
        release_data = None

    if release_data is None or include_prerelease:
        try:
            resp_list = requests.get(_gh_api(f"repos/{repo}/releases?per_page=5"), headers=headers, timeout=timeout)
            if resp_list.status_code == 200:
                items = resp_list.json() or []
                for item in items:
                    if not item.get("draft") and (include_prerelease or not item.get("prerelease")):
                        if release_data is None or is_newer_version(item.get("tag_name", ""), release_data.get("tag_name", "")):
                            release_data = item
                        break
        except Exception:
            pass

    branch_sha = ""
    try:
        b_resp = requests.get(_gh_api(f"repos/{repo}/branches/{branch}"), headers=headers, timeout=timeout)
        if b_resp.status_code == 200:
            branch_sha = ((b_resp.json().get("commit") or {}).get("sha") or "")[:12]
    except Exception:
        branch_sha = ""

    latest_tag = (release_data or {}).get("tag_name") or ""
    assets = [
        {
            "name": a.get("name"),
            "size": a.get("size"),
            "download_url": a.get("browser_download_url"),
        }
        for a in (release_data or {}).get("assets", [])
        if isinstance(a, dict)
    ]
    return {
        "repo": repo,
        "upstream_repo": UPSTREAM_REPO,
        "branch": branch,
        "branch_commit": branch_sha,
        "current_version": APP_VERSION,
        "latest_version": latest_tag,
        "has_update": bool(latest_tag and is_newer_version(latest_tag, APP_VERSION)),
        "prerelease": bool((release_data or {}).get("prerelease", False)),
        "release_url": (release_data or {}).get("html_url", ""),
        "release_notes": ((release_data or {}).get("body") or "")[:1000],
        "assets": assets,
    }


def _select_exe_asset(assets: list[dict[str, Any]], exe_name: str) -> dict[str, Any] | None:
    lower_target = exe_name.lower()
    for asset in assets:
        if str(asset.get("name", "")).lower() == lower_target:
            return asset
    for preferred in ("investmentagent-setup-win64.exe", "investmentagent-win64.exe"):
        for asset in assets:
            if str(asset.get("name", "")).lower() == preferred:
                return asset
    for asset in assets:
        if str(asset.get("name", "")).lower().endswith(".exe"):
            return asset
    return None


def perform_upgrade(
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    apply: bool = False,
    include_prerelease: bool = True,
) -> dict[str, Any]:
    info = check_for_updates(repo=repo, branch=branch, include_prerelease=include_prerelease)
    if not apply:
        return {"status": "checked", **info}

    if getattr(sys, "frozen", False):
        current_exe = Path(sys.executable).resolve()
        asset = _select_exe_asset(info.get("assets", []), current_exe.name)
        if not asset or not asset.get("download_url"):
            return {"status": "no_exe_asset", **info}
        resp = requests.get(asset["download_url"], headers=_github_headers(), timeout=120)
        resp.raise_for_status()
        asset_name = str(asset.get("name", ""))
        if "setup" in asset_name.lower() and asset_name.lower().endswith(".exe"):
            tmp_path = Path(tempfile.gettempdir()) / asset_name
            tmp_path.write_bytes(resp.content)
            subprocess.Popen([str(tmp_path), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return {"status": "silent_installer_started", "installer_path": str(tmp_path), "asset": asset_name, **info}
        staged = current_exe.with_suffix(".new.exe")
        staged.write_bytes(resp.content)
        bat_path = Path(tempfile.gettempdir()) / f"ia_upgrade_{os.getpid()}.bat"
        bat_path.write_text(
            f'@echo off\nping 127.0.0.1 -n 3 > nul\nmove /y "{staged}" "{current_exe}"\nstart "" "{current_exe}"\ndel "%~f0"\n',
            encoding="utf-8",
        )
        subprocess.Popen(["cmd", "/c", str(bat_path)], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return {"status": "staged_exe_upgrade", "staged_path": str(staged), "asset": asset["name"], **info}

    repo_root = Path(__file__).resolve().parent
    if (repo_root / ".git").exists():
        proc = subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return {
            "status": "git_pulled" if proc.returncode == 0 else "git_pull_failed",
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            **info,
        }
    return {"status": "manual_download_required", **info}
