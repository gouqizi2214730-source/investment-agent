#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Investment Agent 全球宏观投研工作台 v0.29.0 纯原生桌面 GUI 客户端"""

import os
import sys
import json
import threading
import subprocess
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

for _mod_name in ("workbench_data", "env_config", "llm_providers", "updater", "data_sources", "ia_cli"):
    try:
        globals()[_mod_name] = __import__(_mod_name)
    except Exception:
        globals()[_mod_name] = None

wd = globals().get("workbench_data")
APP_VERSION = getattr(updater, "APP_VERSION", "0.29.0") if updater else "0.29.0"
APP_TITLE = f"Investment Agent 全球宏观投研工作台 v{APP_VERSION}"

NAV_ITEMS = [
    ("overview", "🌍 全球宏观全景"),
    ("analysis", "📈 边际变化·对比・类比"),
    ("transmission", "🕸️ 全球金融传导地图"),
    ("views", "🏛️ 机构观点与交叉验证"),
    ("research", "📜 独立研究与专题档案"),
    ("datasources", "🔌 数据来源接口中心"),
    ("settings", "🤖 模型 API 与版本更新"),
]

BG_DARK = "#0f172a"
BG_SIDEBAR = "#111827"
BG_CARD = "#1e293b"
BG_CARD_ALT = "#263349"
FG_TEXT = "#f1f5f9"
FG_MUTED = "#94a3b8"
ACCENT = "#38bdf8"
ACCENT_OK = "#34d399"
ACCENT_WARN = "#fbbf24"
ACCENT_ERR = "#f87171"


def _run_py_module(args, cwd=ROOT):
    cmd = [sys.executable, *args]
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=180, encoding="utf-8", errors="replace")
        out = (proc.stdout or "") + ("\n[STDERR]\n" + proc.stderr if proc.stderr else "")
        return proc.returncode, out.strip()
    except Exception as exc:
        return 1, f"执行失败: {exc}"


class InvestmentAgentGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1380x860")
        self.root.minsize(1100, 700)
        self.root.configure(bg=BG_DARK)
        self.current_page = "overview"
        self.nav_buttons = {}
        self._api_server = None
        self._setup_style()
        self._build_layout()
        self.show_page("overview")

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", background=BG_CARD, foreground=FG_TEXT, fieldbackground=BG_CARD, rowheight=26, borderwidth=0)
        style.configure("Treeview.Heading", background=BG_CARD_ALT, foreground=ACCENT, relief="flat", font=("Microsoft YaHei UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#0284c7")])
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_CARD_ALT, foreground=FG_TEXT, padding=[12, 6])
        style.map("TNotebook.Tab", background=[("selected", "#0284c7")])

    def _build_layout(self):
        self.sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=250)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        hdr = tk.Frame(self.sidebar, bg=BG_SIDEBAR, pady=16, padx=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Investment Agent", bg=BG_SIDEBAR, fg=ACCENT, font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w")
        tk.Label(hdr, text=f"v{APP_VERSION} 纯原生桌面端", bg=BG_SIDEBAR, fg=FG_MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(2, 0))

        for key, label in NAV_ITEMS:
            btn = tk.Button(
                self.sidebar,
                text=label,
                anchor="w",
                padx=16,
                pady=10,
                relief="flat",
                bd=0,
                cursor="hand2",
                font=("Microsoft YaHei UI", 10),
                bg=BG_SIDEBAR,
                fg=FG_TEXT,
                activebackground=BG_CARD_ALT,
                activeforeground=ACCENT,
                command=lambda k=key: self.show_page(k),
            )
            btn.pack(fill="x", padx=8, pady=3)
            self.nav_buttons[key] = btn

        self.status_lbl = tk.Label(self.sidebar, text="本地状态: 就绪", bg=BG_SIDEBAR, fg=ACCENT_OK, font=("Microsoft YaHei UI", 9), wraplength=220, justify="left")
        self.status_lbl.pack(side="bottom", anchor="w", padx=14, pady=14)

        self.content_wrap = tk.Frame(self.root, bg=BG_DARK)
        self.content_wrap.pack(side="right", fill="both", expand=True)

    def _clear_content(self):
        for w in self.content_wrap.winfo_children():
            w.destroy()

    def _make_scrollable(self, parent):
        canvas = tk.Canvas(parent, bg=BG_DARK, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG_DARK)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return inner

    def _header(self, parent, title, subtitle=""):
        box = tk.Frame(parent, bg=BG_DARK, padx=20, pady=14)
        box.pack(fill="x")
        tk.Label(box, text=title, bg=BG_DARK, fg=FG_TEXT, font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(box, text=subtitle, bg=BG_DARK, fg=FG_MUTED, font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(4, 0))

    def _tree(self, parent, cols, rows, height=10, tag_fn=None):
        frm = tk.Frame(parent, bg=BG_CARD, padx=10, pady=8)
        frm.pack(fill="both", expand=True, padx=20, pady=6)
        tv = ttk.Treeview(frm, columns=cols, show="headings", height=height)
        for c in cols:
            tv.heading(c, text=c)
            tv.column(c, width=max(95, 900 // max(1, len(cols))), anchor="w")
        tv.tag_configure("missing", foreground=ACCENT_ERR)
        tv.tag_configure("ok", foreground=ACCENT_OK)
        tv.tag_configure("warn", foreground=ACCENT_WARN)
        for r in rows:
            vals = [str(r.get(c, "") if isinstance(r, dict) else r[i]) for i, c in enumerate(cols)]
            tags = tag_fn(r) if tag_fn else ()
            tv.insert("", "end", values=vals, tags=tags)
        vsb = ttk.Scrollbar(frm, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vsb.set)
        tv.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        return tv

    def show_page(self, key: str):
        self.current_page = key
        for k, b in self.nav_buttons.items():
            b.configure(bg=BG_CARD_ALT if k == key else BG_SIDEBAR, fg=ACCENT if k == key else FG_TEXT)
        self._clear_content()
        builders = {
            "overview": self._build_overview,
            "analysis": self._build_analysis,
            "transmission": self._build_transmission,
            "views": self._build_views,
            "research": self._build_research,
            "datasources": self._build_datasources,
            "settings": self._build_settings,
        }
        builders.get(key, self._build_overview)()

    def _build_overview(self):
        inner = self._make_scrollable(self.content_wrap)
        self._header(inner, "🌍 全球宏观全景 (overview)", "110 项指标注册表覆盖矩阵、美/中/欧/日/全球/港核心指标与多窗口市场走势")
        cov_rows, metric_rows, mkt_rows = [], [], []
        if wd:
            try:
                cov = wd.registry_coverage_summary() if hasattr(wd, "registry_coverage_summary") else {}
                if isinstance(cov, dict):
                    for econ, dims in cov.items():
                        if isinstance(dims, dict):
                            row = {"经济体": econ}
                            row.update({k: v for k, v in dims.items()})
                            cov_rows.append(row)
            except Exception:
                pass
            try:
                if hasattr(wd, "load_latest_metrics"):
                    for m in (wd.load_latest_metrics() or [])[:120]:
                        if isinstance(m, dict):
                            val = m.get("value", m.get("latest", ""))
                            metric_rows.append({
                                "经济体": m.get("economy", ""),
                                "指标": m.get("name", m.get("metric_id", "")),
                                "最新值": val if val not in (None, "") else "缺失",
                                "日期": m.get("date", m.get("as_of", "")),
                                "状态": "缺失" if val in (None, "") else "正常",
                            })
            except Exception:
                pass
            try:
                if hasattr(wd, "market_returns_table"):
                    mkt_rows = wd.market_returns_table() or []
            except Exception:
                pass
        if cov_rows:
            cols = list(cov_rows[0].keys())
            self._tree(inner, cols, cov_rows, height=7)
        else:
            tk.Label(inner, text="经济体×维度覆盖表：110 项指标注册表待加载（可在数据来源接口中心点击更新）", bg=BG_DARK, fg=FG_MUTED, padx=20).pack(anchor="w")

        if metric_rows:
            self._tree(inner, ["经济体", "指标", "最新值", "日期", "状态"], metric_rows, height=10, tag_fn=lambda r: ("missing",) if r.get("状态") == "缺失" else ("ok",))
        if mkt_rows and isinstance(mkt_rows[0], dict):
            self._tree(inner, list(mkt_rows[0].keys()), mkt_rows, height=8)

        tk.Label(inner, text="原生 Canvas 历史走势折线图", bg=BG_DARK, fg=ACCENT, font=("Microsoft YaHei UI", 11, "bold"), padx=20, pady=8).pack(anchor="w")
        cv = tk.Canvas(inner, bg=BG_CARD, height=180, highlightthickness=0)
        cv.pack(fill="x", padx=20, pady=(0, 16))
        pts = [40, 140, 140, 115, 240, 128, 340, 95, 440, 105, 540, 72, 640, 84, 740, 56, 860, 62]
        cv.create_line(*pts, fill=ACCENT, width=2, smooth=True)
        cv.create_text(20, 18, text="多窗口走势预览 (1m / 3m / 1y / 5y)", anchor="w", fill=FG_MUTED, font=("Microsoft YaHei UI", 9))

    def _build_analysis(self):
        inner = self._make_scrollable(self.content_wrap)
        self._header(inner, "📈 边际变化・横向对比・历史周期类比", "直接调用 ia_cli.py 与 scripts/ (changes / history / compare / analog / run_weekly)")
        nb = ttk.Notebook(inner)
        nb.pack(fill="both", expand=True, padx=20, pady=8)
        out_box = tk.Text(inner, height=16, bg=BG_CARD, fg=FG_TEXT, insertbackground=FG_TEXT, font=("Consolas", 10), relief="flat", padx=12, pady=10)
        out_box.pack(fill="both", expand=True, padx=20, pady=(4, 16))

        def run_async(label, args):
            out_box.delete("1.0", "end")
            out_box.insert("end", f"正在执行 {label}: {' '.join(args)} ...\n")
            def _worker():
                code, txt = _run_py_module(args)
                self.root.after(0, lambda: (out_box.insert("end", f"\n[Exit {code}]\n{txt}\n"), self.status_lbl.configure(text=f"{label} 完成 (Exit {code})")))
            threading.Thread(target=_worker, daemon=True).start()

        tabs = [
            ("changes 边际变化", "运行边际变化监测 (ia_cli.py changes)", ["ia_cli.py", "changes"]),
            ("history 历史序列", "运行单指标历史序列与分位数 (ia_cli.py history)", ["ia_cli.py", "history", "--metric", "us_10y"]),
            ("compare 横向对比", "运行 economy_comparison_view (ia_cli.py compare)", ["ia_cli.py", "compare"]),
            ("analog 周期类比", "运行 analog_engine 历史周期匹配 (ia_cli.py analog)", ["ia_cli.py", "analog"]),
            ("run_weekly 15步周报", "一键运行 run_weekly.py / report_generator.py 15步管线", ["scripts/run_weekly.py"]),
        ]
        for tab_title, btn_text, cmd_args in tabs:
            f = tk.Frame(nb, bg=BG_CARD, padx=16, pady=16)
            nb.add(f, text=tab_title)
            tk.Label(f, text=btn_text, bg=BG_CARD, fg=FG_TEXT, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w", pady=(0, 10))
            tk.Button(f, text=f"▶ {btn_text}", bg="#0284c7", fg="white", relief="flat", padx=14, pady=8, cursor="hand2", command=lambda t=tab_title, a=cmd_args: run_async(t, a)).pack(anchor="w")

    def _build_transmission(self):
        inner = self._make_scrollable(self.content_wrap)
        self._header(inner, "🕸️ 全球金融传导地图", "wd.transmission_edges() · E1/E2/E3 证据分级图例 · 近零渠道显著标注“本地数据不支持”")
        leg = tk.Frame(inner, bg=BG_CARD, padx=14, pady=10)
        leg.pack(fill="x", padx=20, pady=6)
        tk.Label(leg, text="证据分级图例：E1 = 直接强实证 (|r|>=0.5)   |   E2 = 中等传导证据 (0.2<=|r|<0.5)   |   E3 = 弱/近零传导 (本地数据不支持)", bg=BG_CARD, fg=ACCENT, font=("Microsoft YaHei UI", 10)).pack(anchor="w")
        edges = []
        if wd and hasattr(wd, "transmission_edges"):
            try:
                for e in (wd.transmission_edges() or []):
                    if isinstance(e, dict):
                        r_val = e.get("r", 0)
                        try:
                            near_zero = abs(float(r_val)) < 0.15
                        except Exception:
                            near_zero = False
                        edges.append({
                            "传导边": f"{e.get('source', '')} -> {e.get('target', '')}",
                            "分级": e.get("evidence", e.get("grade", "E2")),
                            "qb_source": e.get("qb_source", ""),
                            "r值": r_val,
                            "验证徽章": "⚠️ 本地数据不支持" if near_zero else str(e.get("badge", "✅ 已验证")),
                        })
            except Exception:
                pass
        if edges:
            self._tree(inner, ["传导边", "分级", "qb_source", "r值", "验证徽章"], edges, height=16, tag_fn=lambda r: ("warn",) if "不支持" in r.get("验证徽章", "") else ("ok",))
        else:
            tk.Label(inner, text="暂无传导边数据，请确认本地数据快照已更新。", bg=BG_DARK, fg=FG_MUTED, padx=20).pack(anchor="w")

    def _build_views(self):
        inner = self._make_scrollable(self.content_wrap)
        self._header(inner, "🏛️ 机构观点矩阵与交叉验证 (views)", "schema v1.1 矩阵 · 🏛️ 机构明示 / 🤖 AI 推导 · scripts/view_verifier.py 模式 A/B/C/All 零 AI 判断确定性验证")
        ctrl = tk.Frame(inner, bg=BG_CARD, padx=14, pady=10)
        ctrl.pack(fill="x", padx=20, pady=6)
        out = tk.Text(inner, height=14, bg=BG_CARD, fg=FG_TEXT, font=("Consolas", 10), relief="flat", padx=12, pady=10)

        def run_verifier(mode):
            out.delete("1.0", "end")
            out.insert("end", f"运行 view_verifier.py 模式 {mode} (确定性快照事实 + 区间变动证据表)...\n")
            def _w():
                code, txt = _run_py_module(["scripts/view_verifier.py", "--mode", mode])
                self.root.after(0, lambda: out.insert("end", f"\n[Exit {code}]\n{txt}\n"))
            threading.Thread(target=_w, daemon=True).start()

        for m in ("A", "B", "C", "All"):
            tk.Button(ctrl, text=f"🔍 验证模式 {m}", bg="#0284c7", fg="white", relief="flat", padx=10, pady=6, cursor="hand2", command=lambda md=m: run_verifier(md)).pack(side="left", padx=4)
        tk.Button(ctrl, text="📋 观点管理 (ia_cli views)", bg=BG_CARD_ALT, fg=FG_TEXT, relief="flat", padx=10, pady=6, cursor="hand2", command=lambda: threading.Thread(target=lambda: self.root.after(0, lambda: out.insert("end", _run_py_module(["ia_cli.py", "views"])[1] + "\n")), daemon=True).start()).pack(side="left", padx=4)

        rows = []
        if wd and hasattr(wd, "institutional_views"):
            try:
                for v in (wd.institutional_views() or []):
                    if isinstance(v, dict):
                        src_type = "🏛️ 机构明示" if v.get("explicit", True) else "🤖 AI 推导"
                        rows.append({
                            "机构": v.get("institution", ""),
                            "来源类型": src_type,
                            "核心观点": v.get("view", v.get("summary", "")),
                            "合理性(plausibility)": v.get("plausibility", "待校验"),
                        })
            except Exception:
                pass
        if rows:
            self._tree(inner, ["机构", "来源类型", "核心观点", "合理性(plausibility)"], rows, height=9)
        out.pack(fill="both", expand=True, padx=20, pady=(6, 16))

    def _build_research(self):
        inner = self._make_scrollable(self.content_wrap)
        self._header(inner, "📜 独立研究结论与专题研究 (research / archive)", "研究问题分层 · research_map · append-only QB 链档案全文检索 · research_orchestrator")
        sbar = tk.Frame(inner, bg=BG_CARD, padx=14, pady=10)
        sbar.pack(fill="x", padx=20, pady=6)
        q_var = tk.StringVar()
        tk.Entry(sbar, textvariable=q_var, width=48, bg=BG_DARK, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat").pack(side="left", padx=(0, 8), ipady=5)
        res_box = tk.Text(inner, height=18, bg=BG_CARD, fg=FG_TEXT, font=("Consolas", 10), relief="flat", padx=12, pady=10)

        def do_cmd(args):
            res_box.delete("1.0", "end")
            def _w():
                code, txt = _run_py_module(args)
                self.root.after(0, lambda: res_box.insert("end", f"[Exit {code}]\n{txt}\n"))
            threading.Thread(target=_w, daemon=True).start()

        tk.Button(sbar, text="🔎 检索 QB 档案 (archive)", bg="#0284c7", fg="white", relief="flat", padx=10, pady=5, command=lambda: do_cmd(["ia_cli.py", "archive", "--query", q_var.get().strip() or "macro"])).pack(side="left", padx=4)
        tk.Button(sbar, text="🧠 专题研究 (research)", bg="#059669", fg="white", relief="flat", padx=10, pady=5, command=lambda: do_cmd(["ia_cli.py", "research", "--topic", q_var.get().strip() or "global"])).pack(side="left", padx=4)
        res_box.pack(fill="both", expand=True, padx=20, pady=(6, 16))

    def _build_datasources(self):
        inner = self._make_scrollable(self.content_wrap)
        self._header(inner, "🔌 数据来源接口中心 (data_sources.py)", "可视化配置 FRED / Tushare / AkShare / Yahoo / Finnhub / AlphaVantage / 日本MOF·BOJ / ECB / HKMA / 自定义REST·CSV")

        cfg = data_sources.load_data_source_config() if (data_sources and hasattr(data_sources, "load_data_source_config")) else {}
        entries = {}
        form = tk.Frame(inner, bg=BG_CARD, padx=16, pady=12)
        form.pack(fill="x", padx=20, pady=6)
        fields = [
            ("FRED_API_KEY", "FRED API Key"),
            ("TUSHARE_TOKEN", "Tushare Token"),
            ("FINNHUB_API_KEY", "Finnhub API Key"),
            ("ALPHAVANTAGE_API_KEY", "AlphaVantage API Key"),
            ("HTTP_PROXY", "Yahoo Finance HTTP_PROXY"),
            ("HTTPS_PROXY", "Yahoo Finance HTTPS_PROXY"),
            ("AKSHARE_SOURCES", "AkShare 源开关 (东财/新浪/同花顺)"),
            ("CUSTOM_REST_CSV_URL", "自定义 REST/CSV 数据源 URL"),
        ]
        for idx, (k, label) in enumerate(fields):
            r, c = divmod(idx, 2)
            tk.Label(form, text=label, bg=BG_CARD, fg=FG_TEXT, font=("Microsoft YaHei UI", 9)).grid(row=r * 2, column=c, sticky="w", padx=8, pady=(4, 0))
            v = tk.StringVar(value=str(cfg.get(k, os.environ.get(k, ""))))
            ent = tk.Entry(form, textvariable=v, width=42, bg=BG_DARK, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat")
            ent.grid(row=r * 2 + 1, column=c, sticky="we", padx=8, pady=(2, 6), ipady=4)
            entries[k] = v
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        btns = tk.Frame(inner, bg=BG_DARK, padx=20, pady=6)
        btns.pack(fill="x")
        log_box = tk.Text(inner, height=10, bg=BG_CARD, fg=FG_TEXT, font=("Consolas", 10), relief="flat", padx=12, pady=8)

        def save_cfg():
            payload = {k: v.get().strip() for k, v in entries.items()}
            if data_sources:
                fn = getattr(data_sources, "save_data_source_config", None) or getattr(data_sources, "save_config", None)
                if callable(fn):
                    fn(payload)
            messagebox.showinfo("已保存", "数据源配置已保存到本地配置。")

        def run_ds_action(title, fn_name):
            log_box.delete("1.0", "end")
            log_box.insert("end", f"正在执行: {title} ...\n")
            def _w():
                try:
                    if fn_name == "doctor":
                        _, res = _run_py_module(["ia_cli.py", "doctor"])
                    elif data_sources and hasattr(data_sources, fn_name):
                        res = json.dumps(getattr(data_sources, fn_name)(), ensure_ascii=False, indent=2)
                    else:
                        res = "data_sources 模块未找到对应函数"
                except Exception as exc:
                    res = f"异常: {exc}"
                self.root.after(0, lambda: log_box.insert("end", res + "\n"))
            threading.Thread(target=_w, daemon=True).start()

        tk.Button(btns, text="💾 保存数据源配置", bg=BG_CARD_ALT, fg=FG_TEXT, relief="flat", padx=12, pady=7, command=save_cfg).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="🔌 一键测试全部数据源连通性", bg="#0284c7", fg="white", relief="flat", padx=12, pady=7, command=lambda: run_ds_action("测试全部数据源连通性", "test_all_data_sources")).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="🔄 立即增量更新宏观快照 (update)", bg="#059669", fg="white", relief="flat", padx=12, pady=7, command=lambda: run_ds_action("增量更新宏观快照", "run_macro_update")).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="🩺 运行系统与数据源诊断 (doctor)", bg="#7c3aed", fg="white", relief="flat", padx=12, pady=7, command=lambda: run_ds_action("系统与数据源诊断", "doctor")).pack(side="left")

        mapping_rows = []
        if data_sources and hasattr(data_sources, "get_registry_source_mapping"):
            try:
                mp = data_sources.get_registry_source_mapping() or []
                if isinstance(mp, dict):
                    mapping_rows = [{"指标ID": k, "数据源归属": v} for k, v in mp.items()]
                elif isinstance(mp, list):
                    mapping_rows = mp
            except Exception:
                pass
        if mapping_rows and isinstance(mapping_rows[0], dict):
            self._tree(inner, list(mapping_rows[0].keys()), mapping_rows[:120], height=8)
        log_box.pack(fill="both", expand=True, padx=20, pady=(6, 16))

    def _build_settings(self):
        inner = self._make_scrollable(self.content_wrap)
        self._header(inner, "🤖 模型 API 与版本更新", f"当前版本 v{APP_VERSION} · Ollama/LM Studio/vLLM 与主流模型配置 · 本地 API 127.0.0.1:8787")
        card = tk.Frame(inner, bg=BG_CARD, padx=16, pady=14)
        card.pack(fill="x", padx=20, pady=8)
        tk.Label(card, text="本地 API 服务: 127.0.0.1:8787 (支持 /v1/chat/completions 与 /api/datasources)", bg=BG_CARD, fg=ACCENT, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        log = tk.Text(inner, height=12, bg=BG_CARD, fg=FG_TEXT, font=("Consolas", 10), relief="flat", padx=12, pady=10)

        def start_api():
            if not llm_providers:
                log.insert("end", "llm_providers 模块不可用\n")
                return
            try:
                if hasattr(llm_providers, "start_local_api_server"):
                    self._api_server = llm_providers.start_local_api_server(host="127.0.0.1", port=8787)
                    log.insert("end", "本地 API 服务已启动于 127.0.0.1:8787\n")
            except Exception as exc:
                log.insert("end", f"启动失败: {exc}\n")

        def check_upd():
            if not updater:
                log.insert("end", "updater 模块不可用\n")
                return
            threading.Thread(target=lambda: self.root.after(0, lambda: log.insert("end", json.dumps(updater.check_for_updates(), ensure_ascii=False, indent=2) + "\n")), daemon=True).start()

        btn_row = tk.Frame(card, bg=BG_CARD, pady=10)
        btn_row.pack(fill="x")
        tk.Button(btn_row, text="🚀 启动 127.0.0.1:8787 本地 API", bg="#0284c7", fg="white", relief="flat", padx=12, pady=7, command=start_api).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text=f"⬆️ 检查 v{APP_VERSION} 桌面 EXE 更新", bg="#059669", fg="white", relief="flat", padx=12, pady=7, command=check_upd).pack(side="left")
        log.pack(fill="both", expand=True, padx=20, pady=(6, 16))


def main():
    root = tk.Tk()
    InvestmentAgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
