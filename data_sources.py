"""Data source interface manager for Investment Agent v0.29.0."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import env_config

CONFIG_JSON_PATH = Path(env_config.DATA_DIR) / "data_sources_config.json"
ENV_FILE_PATH = Path(env_config.PROJECT_ROOT) / ".env"

DEFAULT_SOURCES: dict[str, Any] = {
    "FRED_API_KEY": "",
    "FRED_BASE_URL": "https://api.stlouisfed.org/fred",
    "TUSHARE_TOKEN": "",
    "AKSHARE_ENABLED": "true",
    "AKSHARE_EASTMONEY_ENABLED": "true",
    "AKSHARE_SINA_ENABLED": "true",
    "AKSHARE_THS_ENABLED": "true",
    "YFINANCE_ENABLED": "true",
    "HTTP_PROXY": "",
    "HTTPS_PROXY": "",
    "FINNHUB_API_KEY": "",
    "ALPHAVANTAGE_API_KEY": "",
    "EUROSTAT_BASE_URL": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data",
    "ECB_BASE_URL": "https://data-api.ecb.europa.eu/service/data",
    "BOJ_ESTAT_BASE_URL": "https://api.e-stat.go.jp/rest/3.0/app/json",
    "HKMA_BASE_URL": "https://api.hkma.gov.hk/public/market-data-and-statistics",
    "WORLDBANK_BASE_URL": "https://api.worldbank.org/v2",
    "IMF_BASE_URL": "https://dataservices.imf.org/REST/SDMX_JSON.svc",
    "CUSTOM_SOURCES": [],
}


def load_data_source_config() -> dict[str, Any]:
    cfg: dict[str, Any] = dict(DEFAULT_SOURCES)
    if CONFIG_JSON_PATH.exists():
        try:
            saved = json.loads(CONFIG_JSON_PATH.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                cfg.update(saved)
        except Exception:
            pass
    for key in DEFAULT_SOURCES:
        if key == "CUSTOM_SOURCES":
            continue
        env_val = os.environ.get(key)
        if env_val is not None and env_val != "":
            cfg[key] = env_val
    return cfg


def _write_env_keys(updates: dict[str, str]) -> None:
    lines: list[str] = []
    if ENV_FILE_PATH.exists():
        lines = ENV_FILE_PATH.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        k = stripped.split("=", 1)[0].strip()
        if k in updates:
            new_lines.append(f"{k}={updates[k]}")
            seen.add(k)
        else:
            new_lines.append(line)
    for k, v in updates.items():
        if k not in seen:
            new_lines.append(f"{k}={v}")
    ENV_FILE_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def save_data_source_config(updates: dict[str, Any]) -> dict[str, Any]:
    cfg = load_data_source_config()
    for k, v in updates.items():
        if k in DEFAULT_SOURCES:
            cfg[k] = v
    CONFIG_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_JSON_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    env_updates: dict[str, str] = {}
    for k, v in cfg.items():
        if k == "CUSTOM_SOURCES":
            continue
        s = str(v or "")
        env_updates[k] = s
        if s:
            os.environ[k] = s
    _write_env_keys(env_updates)
    return cfg


def list_data_sources() -> list[dict[str, Any]]:
    cfg = load_data_source_config()
    items = [
        {"id": "fred", "name": "FRED API (US/Global Macro)", "configured": bool(cfg.get("FRED_API_KEY")), "base_url": cfg.get("FRED_BASE_URL")},
        {"id": "akshare", "name": "AkShare (EastMoney/Sina/THS)", "configured": str(cfg.get("AKSHARE_ENABLED", "true")).lower() == "true", "base_url": "akshare://cn-hk-macro"},
        {"id": "tushare", "name": "Tushare Pro", "configured": bool(cfg.get("TUSHARE_TOKEN")), "base_url": "https://api.tushare.pro"},
        {"id": "yfinance", "name": "Yahoo Finance (yfinance)", "configured": str(cfg.get("YFINANCE_ENABLED", "true")).lower() == "true", "base_url": "https://query1.finance.yahoo.com"},
        {"id": "finnhub", "name": "Finnhub Market API", "configured": bool(cfg.get("FINNHUB_API_KEY")), "base_url": "https://finnhub.io/api/v1"},
        {"id": "alphavantage", "name": "Alpha Vantage API", "configured": bool(cfg.get("ALPHAVANTAGE_API_KEY")), "base_url": "https://www.alphavantage.co"},
        {"id": "eurostat", "name": "Eurostat API", "configured": bool(cfg.get("EUROSTAT_BASE_URL")), "base_url": cfg.get("EUROSTAT_BASE_URL")},
        {"id": "ecb", "name": "ECB Data API", "configured": bool(cfg.get("ECB_BASE_URL")), "base_url": cfg.get("ECB_BASE_URL")},
        {"id": "boj_estat", "name": "BOJ / Japan e-Stat API", "configured": bool(cfg.get("BOJ_ESTAT_BASE_URL")), "base_url": cfg.get("BOJ_ESTAT_BASE_URL")},
        {"id": "hkma", "name": "HKMA Public API", "configured": bool(cfg.get("HKMA_BASE_URL")), "base_url": cfg.get("HKMA_BASE_URL")},
        {"id": "worldbank", "name": "World Bank API", "configured": bool(cfg.get("WORLDBANK_BASE_URL")), "base_url": cfg.get("WORLDBANK_BASE_URL")},
        {"id": "imf", "name": "IMF SDMX API", "configured": bool(cfg.get("IMF_BASE_URL")), "base_url": cfg.get("IMF_BASE_URL")},
    ]
    for idx, c in enumerate(cfg.get("CUSTOM_SOURCES") or []):
        if isinstance(c, dict):
            items.append({
                "id": f"custom_{idx}",
                "name": c.get("name") or f"Custom Source #{idx + 1}",
                "configured": bool(c.get("url")),
                "base_url": c.get("url", ""),
                "format": c.get("format", "json"),
            })
    return items


def _http_probe(url: str, headers: dict[str, str] | None = None, timeout: int = 8) -> tuple[bool, int, str]:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "InvestmentAgent/0.29.0"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ms = int((time.time() - start) * 1000)
            return True, resp.status, f"OK ({resp.status}, {ms}ms)"
    except urllib.error.HTTPError as exc:
        return False, exc.code, f"HTTP {exc.code}: {exc.reason}"
    except Exception as exc:
        return False, 0, str(exc)


def test_data_source(source_id: str) -> dict[str, Any]:
    cfg = load_data_source_config()
    if source_id == "fred":
        key = cfg.get("FRED_API_KEY", "")
        base = str(cfg.get("FRED_BASE_URL", DEFAULT_SOURCES["FRED_BASE_URL"])).rstrip("/")
        if not key:
            return {"id": source_id, "ok": False, "message": "Missing FRED_API_KEY"}
        ok, code, msg = _http_probe(f"{base}/series?series_id=GDP&api_key={key}&file_type=json")
        return {"id": source_id, "ok": ok, "status": code, "message": msg}
    if source_id == "yfinance":
        ok, code, msg = _http_probe("https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=5d&interval=1d")
        return {"id": source_id, "ok": ok, "status": code, "message": msg}
    if source_id == "finnhub":
        key = cfg.get("FINNHUB_API_KEY", "")
        if not key:
            return {"id": source_id, "ok": False, "message": "Missing FINNHUB_API_KEY"}
        ok, code, msg = _http_probe(f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={key}")
        return {"id": source_id, "ok": ok, "status": code, "message": msg}
    if source_id == "alphavantage":
        key = cfg.get("ALPHAVANTAGE_API_KEY", "")
        if not key:
            return {"id": source_id, "ok": False, "message": "Missing ALPHAVANTAGE_API_KEY"}
        ok, code, msg = _http_probe(f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey={key}")
        return {"id": source_id, "ok": ok, "status": code, "message": msg}
    if source_id == "worldbank":
        base = str(cfg.get("WORLDBANK_BASE_URL", DEFAULT_SOURCES["WORLDBANK_BASE_URL"])).rstrip("/")
        ok, code, msg = _http_probe(f"{base}/country/USA/indicator/NY.GDP.MKTP.CD?format=json&per_page=1")
        return {"id": source_id, "ok": ok, "status": code, "message": msg}
    if source_id == "hkma":
        base = str(cfg.get("HKMA_BASE_URL", DEFAULT_SOURCES["HKMA_BASE_URL"])).rstrip("/")
        ok, code, msg = _http_probe(f"{base}/hk-interbank-ir-daily?pagesize=1")
        return {"id": source_id, "ok": ok, "status": code, "message": msg}
    if source_id in {"eurostat", "ecb", "boj_estat", "imf"}:
        key_map = {"eurostat": "EUROSTAT_BASE_URL", "ecb": "ECB_BASE_URL", "boj_estat": "BOJ_ESTAT_BASE_URL", "imf": "IMF_BASE_URL"}
        url = str(cfg.get(key_map[source_id], "")).strip()
        if not url:
            return {"id": source_id, "ok": False, "message": f"Missing {key_map[source_id]}"}
        ok, code, msg = _http_probe(url)
        return {"id": source_id, "ok": ok, "status": code, "message": msg}
    if source_id == "akshare":
        try:
            import akshare  # noqa: F401
            return {"id": source_id, "ok": True, "message": "akshare module available"}
        except Exception as exc:
            return {"id": source_id, "ok": False, "message": f"akshare unavailable: {exc}"}
    if source_id == "tushare":
        return {"id": source_id, "ok": bool(cfg.get("TUSHARE_TOKEN")), "message": "Token configured" if cfg.get("TUSHARE_TOKEN") else "Missing TUSHARE_TOKEN"}
    if source_id.startswith("custom_"):
        idx = int(source_id.split("_", 1)[1])
        customs = cfg.get("CUSTOM_SOURCES") or []
        if 0 <= idx < len(customs):
            c = customs[idx]
            ok, code, msg = _http_probe(c.get("url", ""), headers=c.get("headers") or None)
            return {"id": source_id, "ok": ok, "status": code, "message": msg}
    return {"id": source_id, "ok": False, "message": "Unknown data source"}


def test_all_data_sources() -> list[dict[str, Any]]:
    return [test_data_source(item["id"]) for item in list_data_sources()]


def get_registry_source_mapping() -> list[dict[str, Any]]:
    reg_path = Path(env_config.CONFIG_DIR) / "metric_registry.json"
    if not reg_path.exists():
        return []
    try:
        data = json.loads(reg_path.read_text(encoding="utf-8"))
        metrics = data.get("metrics", data) if isinstance(data, dict) else data
        rows: list[dict[str, Any]] = []
        if isinstance(metrics, dict):
            for mid, info in metrics.items():
                if isinstance(info, dict):
                    rows.append({
                        "metric_id": mid,
                        "name": info.get("name", mid),
                        "economy": info.get("economy", ""),
                        "source": info.get("source", info.get("provider", "unknown")),
                        "frequency": info.get("frequency", ""),
                    })
        elif isinstance(metrics, list):
            for info in metrics:
                if isinstance(info, dict):
                    rows.append({
                        "metric_id": info.get("id", info.get("metric_id", "")),
                        "name": info.get("name", ""),
                        "economy": info.get("economy", ""),
                        "source": info.get("source", info.get("provider", "unknown")),
                        "frequency": info.get("frequency", ""),
                    })
        return rows
    except Exception:
        return []


def run_ia_cli_command(args: list[str], timeout: int = 120) -> dict[str, Any]:
    cmd = [sys.executable, str(Path(env_config.PROJECT_ROOT) / "ia_cli.py"), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(env_config.PROJECT_ROOT))
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except Exception as exc:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(exc)}


def run_macro_update() -> dict[str, Any]:
    return run_ia_cli_command(["update"], timeout=300)


def run_system_doctor() -> dict[str, Any]:
    return run_ia_cli_command(["doctor"], timeout=120)
