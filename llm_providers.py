"""Unified LLM provider registry, client, config persistence, and local API server."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

DEFAULT_CONFIG_PATH = Path.home() / ".investment-agent" / "llm_config.json"


def _u(scheme: str, rest: str) -> str:
    return f"{scheme}://{rest}"


@dataclass(frozen=True)
class ProviderPreset:
    key: str
    name: str
    base_url: str
    default_model: str
    api_style: str = "openai"
    is_local: bool = False
    requires_api_key: bool = True
    env_key: str = ""
    env_base_url: str = ""


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "ollama": ProviderPreset(
        key="ollama",
        name="Ollama (Local)",
        base_url=_u("http", "localhost:11434/v1"),
        default_model="qwen2.5:7b",
        is_local=True,
        requires_api_key=False,
        env_base_url="OLLAMA_BASE_URL",
    ),
    "lmstudio": ProviderPreset(
        key="lmstudio",
        name="LM Studio (Local)",
        base_url=_u("http", "localhost:1234/v1"),
        default_model="local-model",
        is_local=True,
        requires_api_key=False,
        env_base_url="LMSTUDIO_BASE_URL",
    ),
    "vllm": ProviderPreset(
        key="vllm",
        name="vLLM (Local)",
        base_url=_u("http", "localhost:8000/v1"),
        default_model="default",
        is_local=True,
        requires_api_key=False,
        env_base_url="VLLM_BASE_URL",
    ),
    "local_openai": ProviderPreset(
        key="local_openai",
        name="Local OpenAI-Compatible",
        base_url=_u("http", "127.0.0.1:8080/v1"),
        default_model="local-model",
        is_local=True,
        requires_api_key=False,
    ),
    "openai": ProviderPreset(
        key="openai",
        name="OpenAI",
        base_url=_u("https", "api.openai.com/v1"),
        default_model="gpt-4o-mini",
        env_key="OPENAI_API_KEY",
        env_base_url="OPENAI_BASE_URL",
    ),
    "deepseek": ProviderPreset(
        key="deepseek",
        name="DeepSeek",
        base_url=_u("https", "api.deepseek.com/v1"),
        default_model="deepseek-chat",
        env_key="DEEPSEEK_API_KEY",
        env_base_url="DEEPSEEK_BASE_URL",
    ),
    "dashscope": ProviderPreset(
        key="dashscope",
        name="Tongyi Qianwen (DashScope)",
        base_url=_u("https", "dashscope.aliyuncs.com/compatible-mode/v1"),
        default_model="qwen-plus",
        env_key="DASHSCOPE_API_KEY",
        env_base_url="DASHSCOPE_BASE_URL",
    ),
    "zhipu": ProviderPreset(
        key="zhipu",
        name="Zhipu GLM",
        base_url=_u("https", "open.bigmodel.cn/api/paas/v4"),
        default_model="glm-4-flash",
        env_key="ZHIPU_API_KEY",
        env_base_url="ZHIPU_BASE_URL",
    ),
    "siliconflow": ProviderPreset(
        key="siliconflow",
        name="SiliconFlow",
        base_url=_u("https", "api.siliconflow.cn/v1"),
        default_model="Qwen/Qwen2.5-7B-Instruct",
        env_key="SILICONFLOW_API_KEY",
        env_base_url="SILICONFLOW_BASE_URL",
    ),
    "moonshot": ProviderPreset(
        key="moonshot",
        name="Moonshot Kimi",
        base_url=_u("https", "api.moonshot.cn/v1"),
        default_model="moonshot-v1-8k",
        env_key="MOONSHOT_API_KEY",
        env_base_url="MOONSHOT_BASE_URL",
    ),
    "anthropic": ProviderPreset(
        key="anthropic",
        name="Anthropic Claude",
        base_url=_u("https", "api.anthropic.com"),
        default_model="claude-3-5-sonnet-latest",
        api_style="anthropic",
        env_key="ANTHROPIC_API_KEY",
        env_base_url="ANTHROPIC_BASE_URL",
    ),
    "gemini": ProviderPreset(
        key="gemini",
        name="Google Gemini",
        base_url=_u("https", "generativelanguage.googleapis.com/v1beta/openai/"),
        default_model="gemini-2.5-flash",
        env_key="GEMINI_API_KEY",
        env_base_url="GEMINI_BASE_URL",
    ),
    "openrouter": ProviderPreset(
        key="openrouter",
        name="OpenRouter",
        base_url=_u("https", "openrouter.ai/api/v1"),
        default_model="openai/gpt-4o-mini",
        env_key="OPENROUTER_API_KEY",
        env_base_url="OPENROUTER_BASE_URL",
    ),
    "custom": ProviderPreset(
        key="custom",
        name="Custom (OpenAI-Compatible)",
        base_url="",
        default_model="",
        requires_api_key=False,
    ),
}


def get_config_path() -> Path:
    custom = os.environ.get("INVESTMENT_AGENT_LLM_CONFIG", "").strip()
    return Path(custom) if custom else DEFAULT_CONFIG_PATH


def load_llm_config() -> dict[str, Any]:
    path = get_config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_llm_config(config: dict[str, Any]) -> Path:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "provider": str(config.get("provider") or "custom").strip().lower(),
        "base_url": str(config.get("base_url") or "").strip(),
        "api_key": str(config.get("api_key") or "").strip(),
        "model": str(config.get("model") or "").strip(),
        "api_style": str(config.get("api_style") or "").strip() or "openai",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def is_local_url(url: str) -> bool:
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def resolve_llm_config(
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    saved = load_llm_config()
    chosen_provider = (
        provider
        or os.environ.get("MODEL_PROVIDER")
        or saved.get("provider")
        or "custom"
    ).strip().lower()
    preset = PROVIDER_PRESETS.get(chosen_provider, PROVIDER_PRESETS["custom"])

    resolved_base_url = (
        base_url
        or os.environ.get("MODEL_BASE_URL")
        or (os.environ.get(preset.env_base_url) if preset.env_base_url else "")
        or saved.get("base_url")
        or preset.base_url
    ).strip()

    resolved_model = (
        model
        or os.environ.get("MODEL_NAME")
        or saved.get("model")
        or preset.default_model
    ).strip()

    resolved_key = (
        api_key
        or os.environ.get("MODEL_API_KEY")
        or (os.environ.get(preset.env_key) if preset.env_key else "")
        or saved.get("api_key")
        or ""
    ).strip()

    local = preset.is_local or is_local_url(resolved_base_url)
    if local and not resolved_key:
        resolved_key = "local"

    api_style = preset.api_style
    if chosen_provider == "custom" and "anthropic" in resolved_base_url.lower():
        api_style = "anthropic"

    missing = []
    if not resolved_base_url:
        missing.append("MODEL_BASE_URL")
    if not resolved_model:
        missing.append("MODEL_NAME")
    if not local and preset.requires_api_key and not resolved_key:
        missing.append("MODEL_API_KEY")

    return {
        "provider": chosen_provider,
        "provider_name": preset.name,
        "base_url": resolved_base_url,
        "api_key": resolved_key,
        "model": resolved_model,
        "api_style": api_style,
        "is_local": local,
        "complete": len(missing) == 0,
        "missing": missing,
    }


def list_provider_presets() -> list[dict[str, Any]]:
    return [
        {
            "key": p.key,
            "name": p.name,
            "base_url": p.base_url,
            "default_model": p.default_model,
            "api_style": p.api_style,
            "is_local": p.is_local,
            "requires_api_key": p.requires_api_key,
        }
        for p in PROVIDER_PRESETS.values()
    ]


def chat_completion(
    messages: list[dict[str, str]],
    config: dict[str, Any] | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    timeout: int = 60,
) -> dict[str, Any]:
    cfg = config or resolve_llm_config()
    if not cfg.get("complete"):
        raise ValueError(f"Incomplete LLM config, missing: {', '.join(cfg.get('missing', []))}")

    base_url = cfg["base_url"].rstrip("/")
    api_key = cfg["api_key"] or "local"
    model = cfg["model"]
    api_style = cfg.get("api_style", "openai")

    if api_style == "anthropic":
        url = base_url if base_url.endswith("/messages") else f"{base_url}/v1/messages"
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        user_messages = [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in messages
            if m.get("role") != "system"
        ]
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system_parts:
            payload["system"] = "\n".join(system_parts)
        resp = requests.post(
            url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        )
        return {"content": text, "model": data.get("model", model), "raw": data}

    url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices") or []
    content = ""
    if choices and isinstance(choices[0], dict):
        content = (choices[0].get("message") or {}).get("content", "")
    return {"content": content, "model": data.get("model", model), "raw": data}


def list_remote_models(config: dict[str, Any] | None = None, timeout: int = 15) -> list[str]:
    cfg = config or resolve_llm_config()
    base_url = (cfg.get("base_url") or "").rstrip("/")
    if not base_url:
        return []
    if cfg.get("api_style") == "anthropic":
        return [cfg.get("model") or "claude-3-5-sonnet-latest"]
    url = f"{base_url}/models"
    headers = {"Authorization": f"Bearer {cfg.get('api_key') or 'local'}"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return [m["id"] for m in data.get("data", []) if isinstance(m, dict) and "id" in m]


def test_connection(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or resolve_llm_config()
    if not cfg.get("complete"):
        return {
            "ok": False,
            "provider": cfg.get("provider"),
            "error": f"Missing required fields: {', '.join(cfg.get('missing', []))}",
        }
    try:
        res = chat_completion(
            [{"role": "user", "content": "Reply with OK."}],
            config=cfg,
            temperature=0.0,
            max_tokens=16,
            timeout=20,
        )
        return {
            "ok": True,
            "provider": cfg.get("provider"),
            "model": res.get("model"),
            "reply": res.get("content", "").strip(),
        }
    except Exception as exc:
        return {"ok": False, "provider": cfg.get("provider"), "error": str(exc)}


def make_api_handler(default_config: dict[str, Any] | None = None):
    class LocalAPIHandler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()

        def do_GET(self) -> None:
            if self.path == "/health":
                cfg = default_config or resolve_llm_config()
                self._send_json(200, {"status": "ok", "provider": cfg.get("provider"), "model": cfg.get("model")})
                return
            if self.path == "/api/providers":
                self._send_json(200, {"providers": list_provider_presets()})
                return
            if self.path == "/v1/models":
                cfg = default_config or resolve_llm_config()
                models = [{"id": cfg.get("model") or p.default_model, "object": "model", "owned_by": p.key} for p in PROVIDER_PRESETS.values() if p.default_model]
                self._send_json(200, {"object": "list", "data": models})
                return
            if self.path == "/api/update/check":
                try:
                    import updater
                    self._send_json(200, updater.check_for_updates())
                except Exception as exc:
                    self._send_json(500, {"error": str(exc)})
                return
            if self.path == "/api/datasources":
                try:
                    import data_sources
                    self._send_json(200, {"datasources": data_sources.list_data_sources(), "registry_mapping": data_sources.get_registry_source_mapping()})
                except Exception as exc:
                    self._send_json(500, {"error": str(exc)})
                return
            self._send_json(404, {"error": "Not found"})

        def do_POST(self) -> None:
            if self.path not in (/"v1/chat/completions", "/api/datasources"):
                self._send_json(404, {"error": "Not found"})
                return
            length = int(self.headers.get("Content-Length", "0") or 0)
            raw_body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                body = json.loads(raw_body.decode("utf-8"))
                if self.path == "/api/datasources":
                    import data_sources
                    action = str(body.get("action", "save")).strip().lower()
                    if action == "save":
                        cfg_data = body.get("config") if isinstance(body.get("config"), dict) else body
                        save_fn = getattr(data_sources, "save_data_source_config", None) or getattr(data_sources, "save_config", None)
                        saved = save_fn(cfg_data) if callable(save_fn) else {}
                        self._send_json(200, {"ok": True, "config": saved})
                    elif action == "test":
                        self._send_json(200, {"ok": True, "results": data_sources.test_all_data_sources()})
                    elif action == "update":
                        self._send_json(200, {"ok": True, "result": data_sources.run_macro_update()})
                    else:
                        self._send_json(400, {"error": f"Unknown action: {action}"})
                    return
                cfg = resolve_llm_config(
                    provider=body.get("provider"),
                    base_url=body.get("base_url"),
                    api_key=body.get("api_key"),
                    model=body.get("model"),
                )
                result = chat_completion(
                    messages=body.get("messages") or [],
                    config=cfg,
                    temperature=float(body.get("temperature", 0.2)),
                    max_tokens=int(body.get("max_tokens", 1024)),
                )
                self._send_json(
                    200,
                    {
                        "object": "chat.completion",
                        "model": result.get("model"),
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": result.get("content", "")},
                                "finish_reason": "stop",
                            }
                        ],
                    },
                )
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            return

    return LocalAPIHandler


def start_local_api_server(
    host: str = "127.0.0.1",
    port: int = 8787,
    config: dict[str, Any] | None = None,
) -> ThreadingHTTPServer:
    handler = make_api_handler(default_config=config)
    return ThreadingHTTPServer((host, port), handler)
