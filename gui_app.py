#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Investment Agent 全球宏观投研工作台 v0.27.0 桌面 GUI 客户端"""

import os
import sys
import json
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

ROOT = os.path.dirname(os.path.abspath(__file__))
_MEIPASS = getattr(sys, "_MEIPASS", None)
for _p in (ROOT, os.path.join(ROOT, "scripts"), *([_MEIPASS, os.path.join(_MEIPASS, "scripts")] if _MEIPASS else [])):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import customtkinter as ctk
    HAS_CTK = True
except Exception:
    ctk = None
    HAS_CTK = False

try:
    import workbench_data
except Exception:
    workbench_data = None

try:
    import llm_providers
except Exception:
    llm_providers = None

try:
    import updater
except Exception:
    updater = None

try:
    import ia_cli
except Exception:
    ia_cli = None

APP_TITLE = "Investment Agent 全球宏观投研工作台 v0.27.0"
APP_VERSION = getattr(updater, "APP_VERSION", "0.27.0") if updater else "0.27.0"
UPSTREAM_REPO = getattr(updater, "UPSTREAM_REPO", "bojing951-hash/investment-agent") if updater else "bojing951-hash/investment-agent"
FONT_FAMILY = "Microsoft YaHei"
LOCAL_API_HOST = "127.0.0.1"
LOCAL_API_PORT = 8787

PROVIDER_OPTIONS = [
    ("Ollama", "ollama"),
    ("LM Studio", "lmstudio"),
    ("vLLM", "vllm"),
    ("DeepSeek", "deepseek"),
    ("OpenAI", "openai"),
    ("通义千问 DashScope", "dashscope"),
    ("智谱 GLM", "zhipu"),
    ("硅基流动 SiliconFlow", "siliconflow"),
    ("Moonshot Kimi", "moonshot"),
    ("Claude", "anthropic"),
    ("Gemini", "gemini"),
    ("OpenRouter", "openrouter"),
    ("自定义接口", "custom"),
]

def _safe_json(obj):
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


def _load_macro_bundle():
    result = {"meta": {}, "overview": [], "market": [], "changes": "", "history": "", "analog": "", "archive": ""}
    if workbench_data is not None:
        for key, fn_name in [
            ("meta", "snapshot_meta"),
            ("overview", "overview_rows"),
            ("market", "market_rows"),
        ]:
            fn = getattr(workbench_data, fn_name, None)
            if callable(fn):
                try:
                    result[key] = fn()
                except Exception:
                    pass
    if ia_cli is not None:
        for key, cmd in [("changes", "changes"), ("history", "history"), ("analog", "analog")]:
            fn = getattr(ia_cli, f"cmd_{cmd}", None) or getattr(ia_cli, cmd, None)
            if callable(fn):
                try:
                    result[key] = _safe_json(fn())
                except Exception:
                    pass
    archive_dir = os.path.join(ROOT, "archive")
    if os.path.isdir(archive_dir):
        files = sorted(os.listdir(archive_dir), reverse=True)[:20]
        result["archive"] = "\n".join(files) if files else "暂无归档报告"
    else:
        result["archive"] = "暂无归档报告目录"
    return result


class InvestmentAgentGUI:
    def __init__(self):
        if HAS_CTK:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()
            self.root.configure(bg="#0f172a")
            self._setup_ttk_dark_style()

        self.root.title(APP_TITLE)
        self.root.geometry("1280x820")
        self.root.minsize(1060, 700)

        self.bg_main = "#0f172a"
        self.bg_card = "#1e293b"
        self.bg_sidebar = "#111827"
        self.accent = "#38bdf8"
        self.fg_text = "#f8fafc"
        self.fg_muted = "#94a3b8"

        self.macro_rows_cache = []
        self.nav_buttons = {}
        self.panels = {}
        self._build_layout()
        self.show_panel("overview")
        self.refresh_macro_data()

    def _setup_ttk_dark_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Dark.TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#1e293b")
        style.configure("Dark.TLabel", background="#0f172a", foreground="#f8fafc", font=(FONT_FAMILY, 10))
        style.configure("Card.TLabel", background="#1e293b", foreground="#f8fafc", font=(FONT_FAMILY, 10))
        style.configure("Treeview", background="#1e293b", foreground="#f8fafc", fieldbackground="#1e293b", rowheight=28, font=(FONT_FAMILY, 10))
        style.configure("Treeview.Heading", background="#334155", foreground="#38bdf8", font=(FONT_FAMILY, 10, "bold"))

    def _make_frame(self, parent, fg_color=None, corner_radius=12):
        if HAS_CTK:
            return ctk.CTkFrame(parent, fg_color=fg_color or self.bg_card, corner_radius=corner_radius)
        return tk.Frame(parent, bg=fg_color or self.bg_card, bd=0, highlightthickness=1, highlightbackground="#334155")

    def _make_label(self, parent, text, size=12, bold=False, color=None, bg=None):
        weight = "bold" if bold else "normal"
        if HAS_CTK:
            return ctk.CTkLabel(parent, text=text, font=(FONT_FAMILY, size, weight), text_color=color or self.fg_text)
        return tk.Label(parent, text=text, font=(FONT_FAMILY, size, weight), fg=color or self.fg_text, bg=bg or self.bg_card)

    def _make_button(self, parent, text, command, fg_color=None, width=140):
        if HAS_CTK:
            return ctk.CTkButton(parent, text=text, command=command, font=(FONT_FAMILY, 12, "bold"), fg_color=fg_color or "#0284c7", hover_color="#0369a1", corner_radius=8, width=width, height=36)
        return tk.Button(parent, text=text, command=command, font=(FONT_FAMILY, 10, "bold"), bg=fg_color or "#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff", relief="flat", padx=12, pady=6, cursor="hand2")

    def _make_entry(self, parent, width=260, show=None):
        if HAS_CTK:
            return ctk.CTkEntry(parent, width=width, font=(FONT_FAMILY, 12), show=show or "")
        return tk.Entry(parent, width=max(18, width // 9), font=(FONT_FAMILY, 10), bg="#0f172a", fg="#f8fafc", insertbackground="#f8fafc", relief="flat", show=show or "")

    def _build_layout(self):
        container = self._make_frame(self.root, fg_color=self.bg_main, corner_radius=0)
        container.pack(fill="both", expand=True)

        sidebar = self._make_frame(container, fg_color=self.bg_sidebar, corner_radius=0)
        sidebar.pack(side="left", fill="y", padx=0, pady=0)
        if not HAS_CTK:
            sidebar.configure(width=240)
            sidebar.pack_propagate(False)

        self._make_label(sidebar, "Investment Agent", size=18, bold=True, color=self.accent, bg=self.bg_sidebar).pack(pady=(22, 4), padx=18, anchor="w")
        self._make_label(sidebar, f"全球宏观投研工作台 v{APP_VERSION}", size=11, color=self.fg_muted, bg=self.bg_sidebar).pack(pady=(0, 20), padx=18, anchor="w")

        nav_items = [
            ("overview", "📊 宏观总览与看板"),
            ("ai", "🤖 AI 投研对话与命令中心"),
            ("settings", "⚙️ 模型与本地 API 配置"),
            ("updater", "🔄 自动更新与工作台工具"),
        ]
        for key, label in nav_items:
            btn = self._make_button(sidebar, label, lambda k=key: self.show_panel(k), fg_color="#1e293b", width=210)
            btn.pack(fill="x", padx=14, pady=6)
            self.nav_buttons[key] = btn

        self.status_label = self._make_label(sidebar, "状态：就绪", size=11, color="#34d399", bg=self.bg_sidebar)
        self.status_label.pack(side="bottom", pady=18, padx=16, anchor="w")

        self.content_area = self._make_frame(container, fg_color=self.bg_main, corner_radius=0)
        self.content_area.pack(side="right", fill="both", expand=True, padx=16, pady=16)

        self._build_overview_panel()
        self._build_ai_panel()
        self._build_settings_panel()
        self._build_updater_panel()

    def show_panel(self, name):
        for k, panel in self.panels.items():
            panel.pack_forget()
            if k in self.nav_buttons:
                if HAS_CTK:
                    self.nav_buttons[k].configure(fg_color="#0284c7" if k == name else "#1e293b")
                else:
                    self.nav_buttons[k].configure(bg="#0284c7" if k == name else "#1e293b")
        if name in self.panels:
            self.panels[name].pack(fill="both", expand=True)

    def set_status(self, text):
        self.root.after(0, lambda: self.status_label.configure(text=f"状态：{text}"))

    def _build_overview_panel(self):
        panel = self._make_frame(self.content_area, fg_color=self.bg_main, corner_radius=0)
        self.panels["overview"] = panel

        header = self._make_frame(panel)
        header.pack(fill="x", pady=(0, 12))
        self._make_label(header, "📊 宏观总览与看板", size=16, bold=True).pack(side="left", padx=16, pady=12)
        self._make_button(header, "🔄 刷新数据", self.refresh_macro_data, width=120).pack(side="right", padx=12, pady=10)
        self.search_entry = self._make_entry(header, width=240)
        self.search_entry.pack(side="right", padx=8, pady=10)
        self.search_entry.bind("<KeyRelease>", lambda _e: self._filter_overview_table())
        self._make_label(header, "🔍 搜索过滤：", size=11, color=self.fg_muted).pack(side="right", padx=(8, 0))

        table_card = self._make_frame(panel)
        table_card.pack(fill="both", expand=True, pady=(0, 12))
        cols = ("indicator", "value", "change", "source")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", height=12)
        for c, title, w in [
            ("indicator", "核心宏观指标", 260),
            ("value", "最新数值", 150),
            ("change", "边际变化", 180),
            ("source", "来源/分类", 180),
        ]:
            self.tree.heading(c, text=title)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=12)

        detail_card = self._make_frame(panel)
        detail_card.pack(fill="x")
        self._make_label(detail_card, "历史序列 / 类比分析 / 归档报告摘要", size=12, bold=True, color=self.accent).pack(anchor="w", padx=14, pady=(10, 4))
        self.overview_detail = tk.Text(detail_card, height=8, bg="#0f172a", fg="#e2e8f0", font=(FONT_FAMILY, 10), relief="flat", wrap="word")
        self.overview_detail.pack(fill="x", padx=14, pady=(0, 12))

    def refresh_macro_data(self):
        self.set_status("正在加载宏观数据...")
        def _worker():
            bundle = _load_macro_bundle()
            rows = []
            for item in (bundle.get("overview") or []) + (bundle.get("market") or []):
                if isinstance(item, dict):
                    rows.append((
                        str(item.get("name") or item.get("indicator") or item.get("key") or "-"),
                        str(item.get("value") or item.get("latest") or "-"),
                        str(item.get("change") or item.get("delta") or "-"),
                        str(item.get("category") or item.get("source") or "宏观/市场"),
                    ))
            detail_text = (
                f"【快照元数据】\n{_safe_json(bundle.get('meta'))}\n\n"
                f"【近期边际变化 (Changes)】\n{bundle.get('changes') or '暂无'}\n\n"
                f"【历史序列 (History)】\n{bundle.get('history') or '暂无'}\n\n"
                f"【历史周期类比 (Analog)】\n{bundle.get('analog') or '暂无'}\n\n"
                f"【归档报告】\n{bundle.get('archive') or '暂无'}"
            )
            def _apply():
                self.macro_rows_cache = rows
                self._filter_overview_table()
                self.overview_detail.delete("1.0", "end")
                self.overview_detail.insert("1.0", detail_text)
                self.set_status(f"已加载 {len(rows)} 条宏观指标")
            self.root.after(0, _apply)
        threading.Thread(target=_worker, daemon=True).start()

    def _filter_overview_table(self):
        kw = self.search_entry.get().strip().lower()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for row in self.macro_rows_cache:
            if not kw or any(kw in str(col).lower() for col in row):
                self.tree.insert("", "end", values=row)

    def _build_ai_panel(self):
        panel = self._make_frame(self.content_area, fg_color=self.bg_main, corner_radius=0)
        self.panels["ai"] = panel

        header = self._make_frame(panel)
        header.pack(fill="x", pady=(0, 10))
        self._make_label(header, "🤖 AI 投研对话与命令中心", size=16, bold=True).pack(side="left", padx=16, pady=12)

        quick_bar = self._make_frame(panel)
        quick_bar.pack(fill="x", pady=(0, 10))
        quick_actions = [
            ("生成宏观全景解读", "请结合当前全球宏观指标生成一份中文宏观全景解读与资产配置建议。"),
            ("近期核心变化分析", "请分析近期核心宏观指标与市场边际变化（Changes）及其传导逻辑。"),
            ("历史周期类比", "请基于当前宏观状态进行历史周期类比分析（Analog）并给出风险提示。"),
            ("运行系统诊断 Doctor", "__CMD_DOCTOR__"),
            ("更新宏观数据", "__CMD_UPDATE__"),
        ]
        for label, prompt in quick_actions:
            self._make_button(quick_bar, label, lambda p=prompt, l=label: self._run_ai_or_cmd(l, p), width=155).pack(side="left", padx=6, pady=10)

        output_card = self._make_frame(panel)
        output_card.pack(fill="both", expand=True, pady=(0, 10))
        self.ai_output = tk.Text(output_card, bg="#0f172a", fg="#f8fafc", font=(FONT_FAMILY, 11), relief="flat", wrap="word")
        self.ai_output.pack(fill="both", expand=True, padx=12, pady=12)

        input_card = self._make_frame(panel)
        input_card.pack(fill="x")
        self.ai_input = self._make_entry(input_card, width=720)
        self.ai_input.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=12)
        self.ai_input.bind("<Return>", lambda _e: self._send_chat())
        self._make_button(input_card, "发送指令", self._send_chat, width=120).pack(side="right", padx=12, pady=10)

    def _append_ai_log(self, title, content):
        def _do():
            self.ai_output.insert("end", f"\n=== {title} ===\n{content}\n")
            self.ai_output.see("end")
        self.root.after(0, _do)

    def _send_chat(self):
        text = self.ai_input.get().strip()
        if not text:
            return
        self.ai_input.delete(0, "end")
        self._run_ai_or_cmd("用户提问", text)

    def _run_ai_or_cmd(self, title, prompt):
        self.set_status(f"正在执行：{title}...")
        self._append_ai_log(title, prompt if not prompt.startswith("__CMD_") else "正在后台执行命令...")
        def _worker():
            try:
                if prompt == "__CMD_DOCTOR__":
                    out = _safe_json(ia_cli.cmd_doctor()) if (ia_cli and hasattr(ia_cli, "cmd_doctor")) else "ia_cli.cmd_doctor 不可用，请检查环境。"
                elif prompt == "__CMD_UPDATE__":
                    out = _safe_json(ia_cli.cmd_update()) if (ia_cli and hasattr(ia_cli, "cmd_update")) else "ia_cli.cmd_update 不可用，请检查数据源。"
                elif llm_providers is not None and hasattr(llm_providers, "chat_completion"):
                    cfg = llm_providers.resolve_llm_config() if hasattr(llm_providers, "resolve_llm_config") else {}
                    resp = llm_providers.chat_completion(
                        messages=[{"role": "system", "content": "你是专业的全球宏观投研分析师，请使用简体中文回答。"}, {"role": "user", "content": prompt}],
                        config=cfg,
                    )
                    out = resp.get("content", _safe_json(resp)) if isinstance(resp, dict) else str(resp)
                elif workbench_data is not None and hasattr(workbench_data, "ask_local"):
                    out = str(workbench_data.ask_local(prompt))
                else:
                    out = "未检测到可用的大模型或本地问答模块，请先在“模型与本地 API 配置”中完成配置。"
            except Exception as exc:
                out = f"执行失败：{exc}"
            self._append_ai_log(f"{title} · 结果", out)
            self.set_status("就绪")
        threading.Thread(target=_worker, daemon=True).start()

    def _build_settings_panel(self):
        panel = self._make_frame(self.content_area, fg_color=self.bg_main, corner_radius=0)
        self.panels["settings"] = panel

        card = self._make_frame(panel)
        card.pack(fill="both", expand=True)
        self._make_label(card, "⚙️ 模型与本地 API 配置", size=16, bold=True).pack(anchor="w", padx=18, pady=(16, 10))

        cfg = llm_providers.load_llm_config() if (llm_providers and hasattr(llm_providers, "load_llm_config")) else {}
        self.provider_var = tk.StringVar(value=PROVIDER_OPTIONS[0][0])
        self._label_map = {label: key for label, key in PROVIDER_OPTIONS}
        self._key_map = {key: label for label, key in PROVIDER_OPTIONS}
        if cfg.get("provider") in self._key_map:
            self.provider_var.set(self._key_map[cfg.get("provider")])

        form = self._make_frame(card, fg_color="#0f172a")
        form.pack(fill="x", padx=18, pady=10)

        self._make_label(form, "模型服务商：", size=12, bg="#0f172a").grid(row=0, column=0, sticky="w", padx=12, pady=10)
        provider_combo = ttk.Combobox(form, textvariable=self.provider_var, values=[x[0] for x in PROVIDER_OPTIONS], state="readonly", width=36)
        provider_combo.grid(row=0, column=1, sticky="w", padx=12, pady=10)
        provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        self._make_label(form, "Base URL：", size=12, bg="#0f172a").grid(row=1, column=0, sticky="w", padx=12, pady=10)
        self.base_url_entry = self._make_entry(form, width=420)
        self.base_url_entry.grid(row=1, column=1, sticky="w", padx=12, pady=10)
        self.base_url_entry.insert(0, str(cfg.get("base_url") or f"http://{LOCAL_API_HOST}:11434/v1"))

        self._make_label(form, "API Key：", size=12, bg="#0f172a").grid(row=2, column=0, sticky="w", padx=12, pady=10)
        self.api_key_entry = self._make_entry(form, width=420, show="*")
        self.api_key_entry.grid(row=2, column=1, sticky="w", padx=12, pady=10)
        if cfg.get("api_key"):
            self.api_key_entry.insert(0, str(cfg.get("api_key")))

        self._make_label(form, "模型名称：", size=12, bg="#0f172a").grid(row=3, column=0, sticky="w", padx=12, pady=10)
        self.model_entry = self._make_entry(form, width=420)
        self.model_entry.grid(row=3, column=1, sticky="w", padx=12, pady=10)
        self.model_entry.insert(0, str(cfg.get("model") or "qwen2.5:14b"))

        btn_row = self._make_frame(card, fg_color=self.bg_card)
        btn_row.pack(fill="x", padx=18, pady=12)
        self._make_button(btn_row, "🔌 测试连接", self._test_llm_conn, width=140).pack(side="left", padx=(0, 10))
        self._make_button(btn_row, "💾 保存配置", self._save_llm_cfg, fg_color="#059669", width=140).pack(side="left", padx=10)

        api_box = self._make_frame(card, fg_color="#0f172a")
        api_box.pack(fill="x", padx=18, pady=12)
        self._make_label(api_box, f"本地 API 服务地址：http://{LOCAL_API_HOST}:{LOCAL_API_PORT}（默认监听 {LOCAL_API_HOST} 端口 {LOCAL_API_PORT}）", size=12, color=self.accent, bg="#0f172a").pack(side="left", padx=12, pady=14)
        self._make_button(api_box, "启动本地 API 服务", self._start_local_api, width=160).pack(side="right", padx=12, pady=10)

        self.settings_status = self._make_label(card, "提示：支持 Ollama / LM Studio / vLLM 本地大模型及主流云端厂商接口。", size=11, color=self.fg_muted)
        self.settings_status.pack(anchor="w", padx=18, pady=8)

    def _on_provider_change(self, _e=None):
        key = self._label_map.get(self.provider_var.get(), "custom")
        presets = getattr(llm_providers, "PROVIDER_PRESETS", {}) if llm_providers else {}
        preset = presets.get(key, {})
        if preset.get("base_url"):
            self.base_url_entry.delete(0, "end")
            self.base_url_entry.insert(0, preset["base_url"])
        if preset.get("default_model"):
            self.model_entry.delete(0, "end")
            self.model_entry.insert(0, preset["default_model"])

    def _collect_llm_cfg(self):
        return {
            "provider": self._label_map.get(self.provider_var.get(), "custom"),
            "base_url": self.base_url_entry.get().strip(),
            "api_key": self.api_key_entry.get().strip(),
            "model": self.model_entry.get().strip(),
        }

    def _save_llm_cfg(self):
        cfg = self._collect_llm_cfg()
        try:
            if llm_providers and hasattr(llm_providers, "save_llm_config"):
                llm_providers.save_llm_config(cfg)
            self.settings_status.configure(text="✅ 配置已保存！")
        except Exception as exc:
            self.settings_status.configure(text=f"❌ 保存失败：{exc}")

    def _test_llm_conn(self):
        cfg = self._collect_llm_cfg()
        self.settings_status.configure(text="⏳ 正在测试连接...")
        def _worker():
            try:
                if llm_providers and hasattr(llm_providers, "test_connection"):
                    res = llm_providers.test_connection(cfg)
                    msg = f"✅ 连接成功：{_safe_json(res)}"
                else:
                    msg = "⚠️ llm_providers.test_connection 不可用"
            except Exception as exc:
                msg = f"❌ 连接失败：{exc}"
            self.root.after(0, lambda: self.settings_status.configure(text=msg[:160]))
        threading.Thread(target=_worker, daemon=True).start()

    def _start_local_api(self):
        def _worker():
            try:
                if llm_providers and hasattr(llm_providers, "start_api_server"):
                    llm_providers.start_api_server(host=LOCAL_API_HOST, port=LOCAL_API_PORT)
                else:
                    subprocess.Popen([sys.executable, os.path.join(ROOT, "launcher.py"), "--mode", "api"])
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("启动失败", str(exc)))
        threading.Thread(target=_worker, daemon=True).start()
        self.settings_status.configure(text=f"🚀 已尝试在 http://{LOCAL_API_HOST}:{LOCAL_API_PORT} 启动本地 API 服务")

    def _build_updater_panel(self):
        panel = self._make_frame(self.content_area, fg_color=self.bg_main, corner_radius=0)
        self.panels["updater"] = panel

        card = self._make_frame(panel)
        card.pack(fill="both", expand=True)
        self._make_label(card, "🔄 自动更新与工作台工具", size=16, bold=True).pack(anchor="w", padx=18, pady=(16, 10))
        self._make_label(card, f"当前版本：v{APP_VERSION}", size=13, bold=True, color=self.accent).pack(anchor="w", padx=18, pady=4)
        self._make_label(card, f"上游同步仓库：{UPSTREAM_REPO}", size=12, color=self.fg_muted).pack(anchor="w", padx=18, pady=4)

        btn_bar = self._make_frame(card, fg_color=self.bg_card)
        btn_bar.pack(fill="x", padx=18, pady=16)
        self._make_button(btn_bar, "🔍 检查更新", self._check_update, width=150).pack(side="left", padx=(0, 10))
        self._make_button(btn_bar, "⬇️ 一键自动下载并升级 EXE", self._do_upgrade, fg_color="#059669", width=220).pack(side="left", padx=10)
        self._make_button(btn_bar, "🌐 启动内置 Web 汉化工作台 (Streamlit)", self._launch_streamlit, fg_color="#7c3aed", width=280).pack(side="left", padx=10)

        self.updater_log = tk.Text(card, height=16, bg="#0f172a", fg="#e2e8f0", font=(FONT_FAMILY, 11), relief="flat", wrap="word")
        self.updater_log.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def _check_update(self):
        self.updater_log.insert("end", "\n正在检查更新...\n")
        def _worker():
            try:
                res = updater.check_for_updates() if (updater and hasattr(updater, "check_for_updates")) else "updater.check_for_updates 不可用"
                msg = _safe_json(res)
            except Exception as exc:
                msg = f"检查更新失败：{exc}"
            self.root.after(0, lambda: self.updater_log.insert("end", f"{msg}\n"))
        threading.Thread(target=_worker, daemon=True).start()

    def _do_upgrade(self):
        self.updater_log.insert("end", "\n正在执行一键自动下载并升级 EXE...\n")
        def _worker():
            try:
                res = updater.perform_upgrade() if (updater and hasattr(updater, "perform_upgrade")) else "updater.perform_upgrade 不可用"
                msg = _safe_json(res)
            except Exception as exc:
                msg = f"升级失败：{exc}"
            self.root.after(0, lambda: self.updater_log.insert("end", f"{msg}\n"))
        threading.Thread(target=_worker, daemon=True).start()

    def _launch_streamlit(self):
        self.updater_log.insert("end", "\n正在启动内置 Web 汉化工作台 (Streamlit)...\n")
        def _worker():
            try:
                app_path = os.path.join(_MEIPASS or ROOT, "app.py")
                subprocess.Popen([sys.executable, "-m", "streamlit", "run", app_path, "--server.headless", "true"])
                webbrowser.open(f"http://{LOCAL_API_HOST}:8501")
            except Exception as exc:
                self.root.after(0, lambda: self.updater_log.insert("end", f"启动失败：{exc}\n"))
        threading.Thread(target=_worker, daemon=True).start()


def main():
    app = InvestmentAgentGUI()
    app.root.mainloop()


if __name__ == "__main__":
    main()

