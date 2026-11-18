#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Investment Agent 全球宏观投研工作台 v0.28.0 原生桌面 GUI 客户端"""

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
for _p in (
    ROOT,
    os.path.join(ROOT, "scripts"),
    *([_MEIPASS, os.path.join(_MEIPASS, "scripts")] if _MEIPASS else []),
):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import customtkinter as ctk
    HAS_CTK = True
except Exception:
    ctk = None
    HAS_CTK = False

try:
    import workbench_data as wd
except Exception:
    wd = None

try:
    import view_store
except Exception:
    view_store = None

try:
    import view_plausibility
except Exception:
    view_plausibility = None

try:
    import view_verifier
except Exception:
    view_verifier = None

try:
    import research_map
except Exception:
    research_map = None

try:
    import research_archive
except Exception:
    research_archive = None

try:
    import env_config
except Exception:
    env_config = None

try:
    import llm_providers
except Exception:
    llm_providers = None

try:
    import updater
except Exception:
    updater = None

APP_VERSION = getattr(updater, "APP_VERSION", "0.28.0") if updater else "0.28.0"
APP_TITLE = f"Investment Agent 全球宏观投研工作台 v{APP_VERSION}"

BG_DARK = "#0f172a"
BG_PANEL = "#1e293b"
BG_CARD = "#162032"
FG_TEXT = "#f8fafc"
FG_MUTED = "#94a3b8"
ACCENT = "#38bdf8"
SUCCESS = "#22c55e"
WARN = "#f59e0b"
DANGER = "#ef4444"

NAV_ITEMS = [
    ("macro", "🌍 全球宏观全景"),
    ("transmission", "🕸️ 全球金融传导地图"),
    ("views", "🏛️ 机构观点矩阵与交叉验证"),
    ("research", "📜 独立研究结论 (QB 链)"),
    ("models", "⚙️ 模型与本地 API 中心"),
    ("updates", "🔄 自动更新与 Web 工作台"),
]

ECONOMY_ORDER = ["US", "CN", "EA", "JP", "GLOBAL", "HK"]
SERIES_WINDOWS = ["全部", "5年", "1年", "6个月", "3个月", "1个月"]


def _safe_str(val, default="-"):
    if val is None or val == "":
        return default
    return str(val)


def _populate_treeview(tree, rows, columns=None, missing_tag=False):
    for item in tree.get_children():
        tree.delete(item)
    if not rows:
        tree["columns"] = ("info",)
        tree.heading("info", text="状态")
        tree.column("info", width=400, anchor="w")
        tree.insert("", "end", values=("暂无数据",))
        return
    if columns is None:
        if isinstance(rows[0], dict):
            columns = list(rows[0].keys())
        else:
            columns = ["值"]
    tree["columns"] = columns
    for col in columns:
        tree.heading(col, text=str(col))
        w = 180 if any(k in str(col) for k in ("指标", "名称", "结论", "标题", "问题", "来源", "渠道", "note")) else 110
        tree.column(col, width=w, minwidth=70, anchor="w")
    for row in rows:
        if isinstance(row, dict):
            vals = [_safe_str(row.get(c, "")) for c in columns]
            is_missing = missing_tag and (row.get("当前值") == "缺失" or "缺失" in str(row.get("状态", "")))
        else:
            vals = [_safe_str(row)]
            is_missing = False
        tags = ("missing",) if is_missing else ()
        tree.insert("", "end", values=vals, tags=tags)


class InvestmentAgentGUI:
    def __init__(self):
        if HAS_CTK:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()
            self.root.configure(bg=BG_DARK)
        self.root.title(APP_TITLE)
        self.root.geometry("1380x860")
        self.root.minsize(1100, 700)

        self._configure_ttk_style()
        self.nav_buttons = {}
        self.pages = {}
        self.current_page = None
        self.current_econ = "US"
        self.macro_snap = None
        self.macro_registry = None
        self.series_metrics_map = {}

        self._build_shell()
        self.show_page("macro")

    def _configure_ttk_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Treeview",
            background=BG_CARD,
            foreground=FG_TEXT,
            fieldbackground=BG_CARD,
            rowheight=26,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background=BG_PANEL,
            foreground=ACCENT,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#1d4ed8")], foreground=[("selected", "#ffffff")])

    def _make_frame(self, parent, bg=BG_DARK):
        if HAS_CTK:
            return ctk.CTkFrame(parent, fg_color=bg)
        return tk.Frame(parent, bg=bg)

    def _make_label(self, parent, text="", font=("Segoe UI", 11), color=FG_TEXT, bg=BG_DARK):
        if HAS_CTK:
            return ctk.CTkLabel(parent, text=text, font=font, text_color=color, anchor="w", justify="left")
        return tk.Label(parent, text=text, font=font, fg=color, bg=bg, anchor="w", justify="left")

    def _make_button(self, parent, text, command, bg="#1d4ed8", width=140):
        if HAS_CTK:
            return ctk.CTkButton(parent, text=text, command=command, fg_color=bg, width=width)
        return tk.Button(parent, text=text, command=command, bg=bg, fg="#ffffff", relief="flat", padx=10, pady=5)

    def _make_treeview(self, parent, height=8):
        wrap = tk.Frame(parent, bg=BG_CARD)
        tree = ttk.Treeview(wrap, show="headings", height=height)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        tree.tag_configure("missing", foreground=DANGER)
        tree.tag_configure("near_zero", foreground=WARN)
        return wrap, tree

    def _make_textbox(self, parent, height=120):
        txt = tk.Text(
            parent,
            bg=BG_CARD,
            fg=FG_TEXT,
            insertbackground=FG_TEXT,
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
            height=max(4, height // 18),
        )
        return txt

    def _build_shell(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        sidebar = self._make_frame(self.root, bg=BG_PANEL)
        sidebar.grid(row=0, column=0, sticky="ns")

        title_lbl = self._make_label(sidebar, f"Investment Agent\nv{APP_VERSION} 桌面工作台", font=("Segoe UI", 14, "bold"), color=ACCENT, bg=BG_PANEL)
        title_lbl.pack(padx=14, pady=(16, 12), fill="x")

        for key, label in NAV_ITEMS:
            btn = self._make_button(
                sidebar,
                text=label,
                command=lambda k=key: self.show_page(k),
                bg="#273549",
                width=220,
            )
            btn.pack(padx=12, pady=5, fill="x")
            self.nav_buttons[key] = btn

        self.status_lbl = self._make_label(sidebar, "状态: 就绪", font=("Segoe UI", 10), color=FG_MUTED, bg=BG_PANEL)
        self.status_lbl.pack(side="bottom", padx=14, pady=12, fill="x")

        self.container = self._make_frame(self.root, bg=BG_DARK)
        self.container.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

    def show_page(self, key):
        for k, btn in self.nav_buttons.items():
            color = "#0284c7" if k == key else "#273549"
            if HAS_CTK:
                btn.configure(fg_color=color)
            else:
                btn.configure(bg=color)
        for p in self.pages.values():
            p.grid_forget()
        if key not in self.pages:
            builder = {
                "macro": self._build_macro_page,
                "transmission": self._build_transmission_page,
                "views": self._build_views_page,
                "research": self._build_research_page,
                "models": self._build_models_page,
                "updates": self._build_updates_page,
            }[key]
            self.pages[key] = builder()
        self.pages[key].grid(row=0, column=0, sticky="nsew")
        self.current_page = key

    def _build_macro_page(self):
        page = self._make_frame(self.container, bg=BG_DARK)
        page.grid_rowconfigure(1, weight=1)
        page.grid_columnconfigure(0, weight=1)

        hdr = self._make_frame(page, bg=BG_PANEL)
        hdr.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 6))
        self._make_label(hdr, "🌍 全球宏观全景 (Global Macro Panorama)", font=("Segoe UI", 15, "bold"), color=ACCENT, bg=BG_PANEL).pack(side="left", padx=12, pady=8)
        self._make_button(hdr, "刷新快照", self._refresh_macro_page, bg="#0284c7", width=100).pack(side="right", padx=12, pady=6)

        canvas_scroll = tk.Canvas(page, bg=BG_DARK, highlightthickness=0)
        vsb = ttk.Scrollbar(page, orient="vertical", command=canvas_scroll.yview)
        body = tk.Frame(canvas_scroll, bg=BG_DARK)
        body.bind("<Configure>", lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")))
        canvas_scroll.create_window((0, 0), window=body, anchor="nw")
        canvas_scroll.configure(yscrollcommand=vsb.set)
        canvas_scroll.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        body.grid_columnconfigure(0, weight=1)

        self.macro_meta_lbl = self._make_label(body, "正在加载快照元数据...", font=("Segoe UI", 11), color=FG_TEXT, bg=BG_DARK)
        self.macro_meta_lbl.grid(row=0, column=0, sticky="ew", padx=8, pady=4)

        self.macro_matrix_note_lbl = self._make_label(body, "【经济体×维度覆盖表】", font=("Segoe UI", 12, "bold"), color=ACCENT, bg=BG_DARK)
        self.macro_matrix_note_lbl.grid(row=1, column=0, sticky="ew", padx=8, pady=(8, 2))
        mx_wrap, self.macro_matrix_tree = self._make_treeview(body, height=6)
        mx_wrap.grid(row=2, column=0, sticky="ew", padx=8, pady=4)

        econ_bar = self._make_frame(body, bg=BG_DARK)
        econ_bar.grid(row=3, column=0, sticky="ew", padx=8, pady=(10, 4))
        self._make_label(econ_bar, "经济体切换:", font=("Segoe UI", 11, "bold"), color=FG_TEXT, bg=BG_DARK).pack(side="left", padx=(0, 8))
        self.econ_btns = {}
        labels_map = getattr(wd, "ECONOMY_LABELS", {}) if wd else {}
        for ec in ECONOMY_ORDER:
            lbl = labels_map.get(ec, ec)
            b = self._make_button(econ_bar, f"{ec} ({lbl})", lambda e=ec: self._select_macro_econ(e), bg="#273549", width=110)
            b.pack(side="left", padx=3)
            self.econ_btns[ec] = b

        self.macro_econ_stat_lbl = self._make_label(body, "指标详情:", font=("Segoe UI", 11), color=WARN, bg=BG_DARK)
        self.macro_econ_stat_lbl.grid(row=4, column=0, sticky="ew", padx=8, pady=2)
        ov_wrap, self.macro_overview_tree = self._make_treeview(body, height=8)
        ov_wrap.grid(row=5, column=0, sticky="ew", padx=8, pady=4)

        self._make_label(body, "【市场 1m/3m/1y/5y 多窗口变化表】", font=("Segoe UI", 12, "bold"), color=ACCENT, bg=BG_DARK).grid(row=6, column=0, sticky="ew", padx=8, pady=(10, 2))
        mw_wrap, self.macro_mkt_tree = self._make_treeview(body, height=7)
        mw_wrap.grid(row=7, column=0, sticky="ew", padx=8, pady=4)

        chart_ctrl = self._make_frame(body, bg=BG_PANEL)
        chart_ctrl.grid(row=8, column=0, sticky="ew", padx=8, pady=(10, 4))
        self._make_label(chart_ctrl, "历史走势折线图:", font=("Segoe UI", 12, "bold"), color=ACCENT, bg=BG_PANEL).pack(side="left", padx=8, pady=6)
        self.series_metric_var = tk.StringVar(value="")
        self.series_metric_cb = ttk.Combobox(chart_ctrl, textvariable=self.series_metric_var, state="readonly", width=36)
        self.series_metric_cb.pack(side="left", padx=6, pady=6)
        self.series_metric_cb.bind("<<ComboboxSelected>>", lambda _e: self._draw_macro_chart())

        self.series_window_var = tk.StringVar(value="1年")
        self.series_window_cb = ttk.Combobox(chart_ctrl, textvariable=self.series_window_var, values=SERIES_WINDOWS, state="readonly", width=10)
        self.series_window_cb.pack(side="left", padx=6, pady=6)
        self.series_window_cb.bind("<<ComboboxSelected>>", lambda _e: self._draw_macro_chart())

        self.series_caption_lbl = self._make_label(chart_ctrl, "", font=("Segoe UI", 10), color=SUCCESS, bg=BG_PANEL)
        self.series_caption_lbl.pack(side="left", padx=10)

        self.macro_chart_canvas = tk.Canvas(body, bg=BG_CARD, height=260, highlightthickness=1, highlightbackground="#334155")
        self.macro_chart_canvas.grid(row=9, column=0, sticky="ew", padx=8, pady=(2, 16))
        self.macro_chart_canvas.bind("<Configure>", lambda _e: self._draw_macro_chart())

        self._refresh_macro_page()
        return page

    def _refresh_macro_page(self):
        if wd is None:
            self.macro_meta_lbl.configure(text="错误: workbench_data 模块未加载")
            return
        try:
            snap, note = wd.latest_snapshot()
            registry = wd.load_registry()
            meta = wd.snapshot_meta(snap)
            self.macro_snap = snap
            self.macro_registry = registry
        except Exception as exc:
            self.macro_meta_lbl.configure(text=f"加载快照失败: {exc}")
            return

        snap_date = meta.get("date") or meta.get("snapshot_date") or "-"
        gate_a = meta.get("gate_a_status") or meta.get("gate_a") or meta.get("gate_status") or "-"
        missing_cnt = meta.get("missing_count", meta.get("missing", "-"))
        degraded_cnt = meta.get("degraded_count", meta.get("degraded", "-"))
        meta_text = f"快照日期: {snap_date}  |  Gate A 状态: {gate_a}  |  缺失: {missing_cnt}  |  降级: {degraded_cnt}  |  备注: {note or '-'}"
        self.macro_meta_lbl.configure(text=meta_text)

        try:
            mx = wd.economy_dimension_matrix(snap, registry)
            mx_rows = mx.get("rows", []) if isinstance(mx, dict) else []
            mx_note = mx.get("note", "") if isinstance(mx, dict) else ""
            self.macro_matrix_note_lbl.configure(text=f"【经济体×维度覆盖表】 {mx_note}")
            _populate_treeview(self.macro_matrix_tree, mx_rows)
        except Exception as exc:
            self.macro_matrix_note_lbl.configure(text=f"【经济体×维度覆盖表】加载失败: {exc}")

        try:
            mw_rows = wd.market_window_rows(snap, registry)
            _populate_treeview(self.macro_mkt_tree, mw_rows, missing_tag=True)
        except Exception:
            _populate_treeview(self.macro_mkt_tree, [])

        try:
            capable = wd.series_capable_metrics(snap, registry) or []
            self.series_metrics_map = {}
            display_list = []
            for item in capable:
                if isinstance(item, dict):
                    mid = item.get("id") or item.get("metric_id") or item.get("code") or ""
                    mname = item.get("name") or item.get("label") or mid
                else:
                    mid = str(item)
                    mname = mid
                label = f"{mid} - {mname}" if mname != mid else mid
                self.series_metrics_map[label] = mid
                display_list.append(label)
            self.series_metric_cb["values"] = display_list
            if display_list and self.series_metric_var.get() not in self.series_metrics_map:
                self.series_metric_var.set(display_list[0])
        except Exception:
            self.series_metric_cb["values"] = []

        self._select_macro_econ(self.current_econ)
        self._draw_macro_chart()

    def _select_macro_econ(self, econ):
        self.current_econ = econ
        for ec, b in self.econ_btns.items():
            c = "#0284c7" if ec == econ else "#273549"
            if HAS_CTK:
                b.configure(fg_color=c)
            else:
                b.configure(bg=c)
        if wd is None or self.macro_snap is None:
            return
        try:
            rows = wd.overview_rows(self.macro_snap, self.macro_registry, econ) or []
            missing_n = sum(1 for r in rows if isinstance(r, dict) and r.get("当前值") == "缺失")
            labels_map = getattr(wd, "ECONOMY_LABELS", {})
            econ_name = labels_map.get(econ, econ)
            self.macro_econ_stat_lbl.configure(
                text=f"当前经济体: {econ} ({econ_name})  |  总指标数: {len(rows)}  |  当前值 == '缺失' 项数: {missing_n}"
            )
            _populate_treeview(self.macro_overview_tree, rows, missing_tag=True)
        except Exception as exc:
            self.macro_econ_stat_lbl.configure(text=f"加载 {econ} 指标失败: {exc}")

    def _draw_macro_chart(self):
        c = self.macro_chart_canvas
        c.delete("all")
        w = max(c.winfo_width(), 640)
        h = max(c.winfo_height(), 240)
        if wd is None or self.macro_snap is None:
            return
        label = self.series_metric_var.get()
        metric_id = self.series_metrics_map.get(label)
        window = self.series_window_var.get() or "1年"
        if not metric_id:
            c.create_text(w // 2, h // 2, text="请选择可绘制历史序列的指标", fill=FG_MUTED, font=("Segoe UI", 11))
            return
        try:
            res = wd.metric_series(metric_id, self.macro_snap)
            if isinstance(res, dict):
                dates, values = res.get("dates", []), res.get("values", [])
            else:
                dates, values = res[0], res[1]
            sliced = wd.slice_series_window(dates, values, window)
            if isinstance(sliced, dict):
                d_sub, v_sub = sliced.get("dates", []), sliced.get("values", [])
            else:
                d_sub, v_sub = sliced[0], sliced[1]
            try:
                cap = wd.series_change_caption(d_sub, v_sub)
            except TypeError:
                cap = wd.series_change_caption(dates, values, window)
            self.series_caption_lbl.configure(text=_safe_str(cap, ""))
        except Exception as exc:
            c.create_text(w // 2, h // 2, text=f"序列加载失败: {exc}", fill=DANGER, font=("Segoe UI", 10))
            return

        pts = [(d, float(v)) for d, v in zip(d_sub, v_sub) if v is not None]
        if len(pts) < 2:
            c.create_text(w // 2, h // 2, text="有效数据点不足 2 个，无法绘制折线", fill=FG_MUTED, font=("Segoe UI", 11))
            return

        pad_l, pad_r, pad_t, pad_b = 65, 25, 22, 32
        pw = max(w - pad_l - pad_r, 50)
        ph = max(h - pad_t - pad_b, 50)
        ys = [p[1] for p in pts]
        ymin, ymax = min(ys), max(ys)
        if ymax == ymin:
            ymax = ymin + 1.0

        c.create_line(pad_l, pad_t, pad_l, h - pad_b, fill="#475569")
        c.create_line(pad_l, h - pad_b, w - pad_r, h - pad_b, fill="#475569")
        for i in range(4):
            gy = pad_t + ph * i / 3.0
            val = ymax - (ymax - ymin) * i / 3.0
            c.create_line(pad_l, gy, w - pad_r, gy, fill="#1e293b", dash=(2, 4))
            c.create_text(pad_l - 6, gy, text=f"{val:.2f}", anchor="e", fill=FG_MUTED, font=("Consolas", 9))

        coords = []
        n = len(pts)
        for idx, (_d, yv) in enumerate(pts):
            px = pad_l + pw * idx / (n - 1)
            py = pad_t + ph * (1.0 - (yv - ymin) / (ymax - ymin))
            coords.extend([px, py])
        c.create_line(*coords, fill=ACCENT, width=2, smooth=False)
        c.create_text(pad_l, h - 14, text=str(pts[0][0]), anchor="w", fill=FG_MUTED, font=("Consolas", 9))
        c.create_text(w - pad_r, h - 14, text=str(pts[-1][0]), anchor="e", fill=FG_MUTED, font=("Consolas", 9))

    def _build_transmission_page(self):
        page = self._make_frame(self.container, bg=BG_DARK)
        page.grid_rowconfigure(2, weight=1)
        page.grid_columnconfigure(0, weight=1)

        hdr = self._make_frame(page, bg=BG_PANEL)
        hdr.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 6))
        self._make_label(hdr, "🕸️ 全球金融传导地图 (Transmission Edges)", font=("Segoe UI", 15, "bold"), color=ACCENT, bg=BG_PANEL).pack(side="left", padx=12, pady=8)
        self._make_button(hdr, "刷新传导图", self._refresh_transmission_page, bg="#0284c7", width=110).pack(side="right", padx=12, pady=6)

        self.trans_rule_lbl = self._make_label(page, "证据分级与展示规则加载中...", font=("Segoe UI", 10), color=FG_TEXT, bg=BG_DARK)
        self.trans_rule_lbl.grid(row=1, column=0, sticky="ew", padx=8, pady=4)

        paned = ttk.PanedWindow(page, orient="vertical")
        paned.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)

        f_strong = self._make_frame(paned, bg=BG_DARK)
        self._make_label(f_strong, "强传导边 (strong)", font=("Segoe UI", 12, "bold"), color=SUCCESS, bg=BG_DARK).pack(anchor="w", padx=6, pady=2)
        sw, self.trans_strong_tree = self._make_treeview(f_strong, height=7)
        sw.pack(fill="both", expand=True, padx=6, pady=2)
        paned.add(f_strong, weight=2)

        f_nz = self._make_frame(paned, bg=BG_DARK)
        self._make_label(f_nz, "⚠️ 近零 / 不支持渠道 (near_zero) —— 【本地数据不支持】", font=("Segoe UI", 12, "bold"), color=WARN, bg=BG_DARK).pack(anchor="w", padx=6, pady=2)
        nw, self.trans_nz_tree = self._make_treeview(f_nz, height=6)
        nw.pack(fill="both", expand=True, padx=6, pady=2)
        paned.add(f_nz, weight=2)

        f_sum = self._make_frame(paned, bg=BG_DARK)
        self._make_label(f_sum, "结构性总结与机制发现 (structural_summary & mechanism_findings)", font=("Segoe UI", 11, "bold"), color=ACCENT, bg=BG_DARK).pack(anchor="w", padx=6, pady=2)
        self.trans_summary_txt = self._make_textbox(f_sum, height=120)
        self.trans_summary_txt.pack(fill="both", expand=True, padx=6, pady=2)
        paned.add(f_sum, weight=1)

        self._refresh_transmission_page()
        return page

    def _refresh_transmission_page(self):
        if wd is None:
            return
        try:
            doc = wd.transmission_edges() or {}
        except Exception as exc:
            self.trans_rule_lbl.configure(text=f"加载传导边失败: {exc}")
            return

        grading = doc.get("evidence_grading", {})
        rule = doc.get("display_rule", "")
        g_str = " | ".join(f"{k}: {v}" for k, v in grading.items()) if isinstance(grading, dict) else str(grading)
        self.trans_rule_lbl.configure(text=f"证据分级 (E1/E2/E3): {g_str}\n展示规则: {rule}")

        def _fmt_edges(edges, is_nz=False):
            out = []
            for e in (edges or []):
                qb = e.get("qb_source", "")
                try:
                    badge = wd.edge_verification_badge(qb)
                except Exception:
                    badge = qb
                row = {
                    "传导路径": f"{e.get('from', '')} -> {e.get('to', '')}",
                    "渠道名称": e.get("channel_label", ""),
                    "r": e.get("r", ""),
                    "n": e.get("n", ""),
                    "window": e.get("window", ""),
                    "evidence_level": e.get("evidence_level", ""),
                    "qb_source": qb,
                    "验证徽章": badge,
                }
                if is_nz:
                    row["数据支持状态"] = "本地数据不支持"
                out.append(row)
            return out

        _populate_treeview(self.trans_strong_tree, _fmt_edges(doc.get("strong", []), False))
        _populate_treeview(self.trans_nz_tree, _fmt_edges(doc.get("near_zero", []), True))

        self.trans_summary_txt.delete("1.0", "end")
        s_sum = doc.get("structural_summary", "")
        m_find = doc.get("mechanism_findings", "")
        text_out = f"=== structural_summary ===\n{json.dumps(s_sum, ensure_ascii=False, indent=2) if isinstance(s_sum, (dict, list)) else s_sum}\n\n"
        text_out += f"=== mechanism_findings ===\n{json.dumps(m_find, ensure_ascii=False, indent=2) if isinstance(m_find, (dict, list)) else m_find}"
        self.trans_summary_txt.insert("1.0", text_out)

    def _build_views_page(self):
        page = self._make_frame(self.container, bg=BG_DARK)
        page.grid_rowconfigure(2, weight=1)
        page.grid_columnconfigure(0, weight=1)

        hdr = self._make_frame(page, bg=BG_PANEL)
        hdr.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 6))
        self._make_label(hdr, "🏛️ 机构观点矩阵与交叉验证 (Views Matrix & Verifier)", font=("Segoe UI", 15, "bold"), color=ACCENT, bg=BG_PANEL).pack(side="left", padx=12, pady=8)
        self._make_button(hdr, "运行确定性交叉验证 (view_verifier)", self._run_view_verifier, bg="#059669", width=240).pack(side="right", padx=8, pady=6)
        self._make_button(hdr, "刷新矩阵", self._refresh_views_page, bg="#0284c7", width=100).pack(side="right", padx=6, pady=6)

        self.views_meta_lbl = self._make_label(page, "正在加载机构观点矩阵...", font=("Segoe UI", 10), color=FG_TEXT, bg=BG_DARK)
        self.views_meta_lbl.grid(row=1, column=0, sticky="ew", padx=8, pady=4)

        paned = ttk.PanedWindow(page, orient="vertical")
        paned.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)

        f_top = self._make_frame(paned, bg=BG_DARK)
        self._make_label(f_top, "机构观点列表 (点击行查看 core_views / forecasts 与机构明示/AI推导标注)", font=("Segoe UI", 11, "bold"), color=ACCENT, bg=BG_DARK).pack(anchor="w", padx=6, pady=2)
        vw, self.views_tree = self._make_treeview(f_top, height=7)
        vw.pack(fill="both", expand=True, padx=6, pady=2)
        self.views_tree.bind("<<TreeviewSelect>>", self._on_select_view)
        paned.add(f_top, weight=2)

        f_mid = self._make_frame(paned, bg=BG_DARK)
        self._make_label(f_mid, "选中机构观点详情 (🏛️ 机构明示 vs 🤖 AI 推导)", font=("Segoe UI", 11, "bold"), color=SUCCESS, bg=BG_DARK).pack(anchor="w", padx=6, pady=2)
        self.view_detail_txt = self._make_textbox(f_mid, height=160)
        self.view_detail_txt.pack(fill="both", expand=True, padx=6, pady=2)
        paned.add(f_mid, weight=2)

        f_bot = self._make_frame(paned, bg=BG_DARK)
        self._make_label(f_bot, "确定性验证：【快照事实 + 区间变动证据表（零 AI 判断）】与 view_plausibility 结果", font=("Segoe UI", 11, "bold"), color=WARN, bg=BG_DARK).pack(anchor="w", padx=6, pady=2)
        self.view_verify_txt = self._make_textbox(f_bot, height=160)
        self.view_verify_txt.pack(fill="both", expand=True, padx=6, pady=2)
        paned.add(f_bot, weight=2)

        self.views_rows_cache = []
        self._refresh_views_page()
        return page

    def _refresh_views_page(self):
        if wd is None:
            return
        try:
            vm = wd.views_matrix() or {}
        except Exception as exc:
            self.views_meta_lbl.configure(text=f"加载 views_matrix 失败: {exc}")
            return
        sv = vm.get("schema_version", "-")
        matrix = vm.get("matrix", {})
        rows = vm.get("rows", [])
        self.views_rows_cache = rows
        m_keys = len(matrix) if isinstance(matrix, (dict, list)) else 0
        self.views_meta_lbl.configure(text=f"Schema 版本: {sv}  |  矩阵维度项: {m_keys}  |  机构观点行数: {len(rows)}")
        _populate_treeview(self.views_tree, rows)

    def _on_select_view(self, _event=None):
        sel = self.views_tree.selection()
        if not sel:
            return
        idx = self.views_tree.index(sel[0])
        if idx >= len(self.views_rows_cache):
            return
        row = self.views_rows_cache[idx]
        view_id = row.get("view_id") or row.get("id") or ""
        self.view_detail_txt.delete("1.0", "end")
        if view_store is None or not view_id:
            self.view_detail_txt.insert("1.0", json.dumps(row, ensure_ascii=False, indent=2))
            return
        try:
            doc = view_store.get_view(view_id) or {}
        except Exception as exc:
            self.view_detail_txt.insert("1.0", f"get_view({view_id}) 失败: {exc}")
            return

        def _tag_source(item):
            if not isinstance(item, dict):
                return str(item)
            src = item.get("attribution") or item.get("source_type") or item.get("type") or ""
            badge = "🏛️ 机构明示" if src == "institution_stated" else ("🤖 AI 推导" if src == "ai_inferred" else src)
            return f"[{badge}] {json.dumps(item, ensure_ascii=False)}"

        lines = [f"view_id: {view_id}", "=== core_views ==="]
        for cv in (doc.get("core_views") or []):
            lines.append("  • " + _tag_source(cv))
        lines.append("\n=== forecasts ===")
        for fc in (doc.get("forecasts") or []):
            lines.append("  • " + _tag_source(fc))
        self.view_detail_txt.insert("1.0", "\n".join(lines))

    def _run_view_verifier(self):
        self.view_verify_txt.delete("1.0", "end")
        self.view_verify_txt.insert("1.0", "正在运行确定性交叉验证 (view_verifier & view_plausibility)...")

        def _worker():
            out_parts = []
            verifier_script = os.path.join(ROOT, "scripts", "view_verifier.py")
            if os.path.exists(verifier_script):
                try:
                    proc = subprocess.run(
                        [sys.executable, verifier_script, "--mode", "all"],
                        capture_output=True, text=True, timeout=30, cwd=ROOT,
                    )
                    out_parts.append("=== view_verifier.py --mode all ===")
                    out_parts.append(proc.stdout or proc.stderr or "(无输出)")
                except Exception as exc:
                    out_parts.append(f"view_verifier 子进程异常: {exc}")
            elif view_verifier is not None:
                out_parts.append(f"=== view_verifier 模块已加载: {dir(view_verifier)[:8]} ===")

            if view_plausibility is not None:
                try:
                    if hasattr(view_plausibility, "check_all"):
                        res = view_plausibility.check_all()
                        out_parts.append("\n=== view_plausibility.check_all() ===")
                        out_parts.append(json.dumps(res, ensure_ascii=False, indent=2))
                    else:
                        out_parts.append("\n=== view_plausibility 模块可用 ===")
                except Exception as exc:
                    out_parts.append(f"\nview_plausibility 异常: {exc}")

            final_txt = "\n".join(out_parts) or "未检测到可执行的验证结果。"
            self.root.after(0, lambda: (self.view_verify_txt.delete("1.0", "end"), self.view_verify_txt.insert("1.0", final_txt)))

        threading.Thread(target=_worker, daemon=True).start()

    def _build_research_page(self):
        page = self._make_frame(self.container, bg=BG_DARK)
        page.grid_rowconfigure(2, weight=1)
        page.grid_columnconfigure(0, weight=1)

        hdr = self._make_frame(page, bg=BG_PANEL)
        hdr.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 6))
        self._make_label(hdr, "📜 独立研究结论 (QB 链 & Agent Native 研究)", font=("Segoe UI", 15, "bold"), color=ACCENT, bg=BG_PANEL).pack(side="left", padx=12, pady=8)
        self._make_button(hdr, "刷新研究档案", self._refresh_research_page, bg="#0284c7", width=120).pack(side="right", padx=12, pady=6)

        trig = self._make_frame(page, bg=BG_PANEL)
        trig.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 6))
        self._make_label(trig, "Agent Native 专题研究触发:", font=("Segoe UI", 11, "bold"), color=FG_TEXT, bg=BG_PANEL).pack(side="left", padx=10, pady=6)
        self.research_topic_var = tk.StringVar(value="")
        ent = tk.Entry(trig, textvariable=self.research_topic_var, bg=BG_CARD, fg=FG_TEXT, insertbackground=FG_TEXT, width=52, font=("Segoe UI", 10))
        ent.pack(side="left", padx=8, pady=6)
        self._make_button(trig, "触发专题研究", self._run_topic_research, bg="#7c3aed", width=130).pack(side="left", padx=6, pady=6)

        paned = ttk.PanedWindow(page, orient="vertical")
        paned.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)

        f_map = self._make_frame(paned, bg=BG_DARK)
        self._make_label(f_map, "研究地图与问题分层 (research_questions & research_map.build_map)", font=("Segoe UI", 11, "bold"), color=ACCENT, bg=BG_DARK).pack(anchor="w", padx=6, pady=2)
        self.research_map_txt = self._make_textbox(f_map, height=130)
        self.research_map_txt.pack(fill="both", expand=True, padx=6, pady=2)
        paned.add(f_map, weight=1)

        f_arch = self._make_frame(paned, bg=BG_DARK)
        self._make_label(f_arch, "本地 Append-Only 研究档案 (QB 链, 点击行查看完整结论与证据链)", font=("Segoe UI", 11, "bold"), color=SUCCESS, bg=BG_DARK).pack(anchor="w", padx=6, pady=2)
        aw, self.research_tree = self._make_treeview(f_arch, height=7)
        aw.pack(fill="both", expand=True, padx=6, pady=2)
        self.research_tree.bind("<<TreeviewSelect>>", self._on_select_research)
        paned.add(f_arch, weight=2)

        f_full = self._make_frame(paned, bg=BG_DARK)
        self._make_label(f_full, "完整研究结论与证据链 (load_research_full)", font=("Segoe UI", 11, "bold"), color=WARN, bg=BG_DARK).pack(anchor="w", padx=6, pady=2)
        self.research_full_txt = self._make_textbox(f_full, height=160)
        self.research_full_txt.pack(fill="both", expand=True, padx=6, pady=2)
        paned.add(f_full, weight=2)

        self.research_rows_cache = []
        self._refresh_research_page()
        return page

    def _refresh_research_page(self):
        self.research_map_txt.delete("1.0", "end")
        parts = []
        if wd is not None:
            try:
                qs = wd.research_questions()
                parts.append("=== research_questions() ===")
                parts.append(json.dumps(qs, ensure_ascii=False, indent=2))
            except Exception as exc:
                parts.append(f"research_questions 失败: {exc}")
        if research_map is not None:
            try:
                rmap = research_map.build_map()
                parts.append("\n=== research_map.build_map() ===")
                parts.append(json.dumps(rmap, ensure_ascii=False, indent=2))
            except Exception as exc:
                parts.append(f"research_map.build_map 失败: {exc}")
        self.research_map_txt.insert("1.0", "\n".join(parts))

        if wd is not None:
            try:
                rows = wd.research_archive_rows(limit=100) or []
                self.research_rows_cache = rows
                _populate_treeview(self.research_tree, rows)
            except Exception:
                _populate_treeview(self.research_tree, [])

    def _on_select_research(self, _event=None):
        sel = self.research_tree.selection()
        if not sel:
            return
        idx = self.research_tree.index(sel[0])
        if idx >= len(self.research_rows_cache):
            return
        row = self.research_rows_cache[idx]
        qid = row.get("query_id") or row.get("id") or ""
        self.research_full_txt.delete("1.0", "end")
        if research_archive is None or not qid:
            self.research_full_txt.insert("1.0", json.dumps(row, ensure_ascii=False, indent=2))
            return
        try:
            full = research_archive.load_research_full(qid)
            self.research_full_txt.insert("1.0", json.dumps(full, ensure_ascii=False, indent=2) if isinstance(full, (dict, list)) else str(full))
        except Exception as exc:
            self.research_full_txt.insert("1.0", f"load_research_full({qid}) 失败: {exc}")

    def _run_topic_research(self):
        topic = self.research_topic_var.get().strip()
        if not topic:
            messagebox.showinfo("提示", "请输入要研究的宏观专题问题。")
            return
        self.status_lbl.configure(text=f"正在研究: {topic[:18]}...")

        def _worker():
            ia_script = os.path.join(ROOT, "ia_cli.py")
            try:
                proc = subprocess.run(
                    [sys.executable, ia_script, "research", topic],
                    capture_output=True, text=True, timeout=60, cwd=ROOT,
                )
                msg = proc.stdout or proc.stderr or "研究执行完成"
            except Exception as exc:
                msg = f"专题研究执行失败: {exc}"
            self.root.after(0, lambda: (
                self.status_lbl.configure(text="状态: 就绪"),
                self.research_full_txt.delete("1.0", "end"),
                self.research_full_txt.insert("1.0", msg),
                self._refresh_research_page(),
            ))

        threading.Thread(target=_worker, daemon=True).start()

    def _build_models_page(self):
        page = self._make_frame(self.container, bg=BG_DARK)
        hdr = self._make_frame(page, bg=BG_PANEL)
        hdr.pack(fill="x", padx=4, pady=(0, 8))
        self._make_label(hdr, "⚙️ 模型与本地 API 中心 (Ollama / LM Studio / vLLM / 8787)", font=("Segoe UI", 15, "bold"), color=ACCENT, bg=BG_PANEL).pack(side="left", padx=12, pady=8)

        form = self._make_frame(page, bg=BG_CARD)
        form.pack(fill="x", padx=8, pady=6)
        providers = list(getattr(llm_providers, "PROVIDERS", {}).keys()) if llm_providers else ["ollama", "lmstudio", "vllm", "openai", "deepseek", "anthropic", "gemini"]
        default_url = "http:" + "//127.0.0.1:11434/v1"
        self.prov_var = tk.StringVar(value=providers[0] if providers else "ollama")
        self.base_url_var = tk.StringVar(value=os.environ.get("OPENAI_BASE_URL", default_url))
        self.api_key_var = tk.StringVar(value=os.environ.get("OPENAI_API_KEY", ""))
        self.model_var = tk.StringVar(value=os.environ.get("IA_MODEL", "qwen2.5:14b"))

        for r, (lbl, var) in enumerate([("厂商/后端:", self.prov_var), ("Base URL:", self.base_url_var), ("API Key:", self.api_key_var), ("默认模型:", self.model_var)]):
            self._make_label(form, lbl, font=("Segoe UI", 11), color=FG_TEXT, bg=BG_CARD).grid(row=r, column=0, padx=12, pady=6, sticky="w")
            if r == 0:
                ttk.Combobox(form, textvariable=var, values=providers, state="readonly", width=42).grid(row=r, column=1, padx=8, pady=6, sticky="w")
            else:
                tk.Entry(form, textvariable=var, bg=BG_DARK, fg=FG_TEXT, insertbackground=FG_TEXT, width=46, show="*" if r == 2 else "").grid(row=r, column=1, padx=8, pady=6, sticky="w")

        btns = self._make_frame(page, bg=BG_DARK)
        btns.pack(fill="x", padx=8, pady=8)
        self._make_button(btns, "保存配置到 .env", self._save_model_env, bg="#059669", width=150).pack(side="left", padx=6)
        self._make_button(btns, "启动 8787 本地 API", self._start_local_api, bg="#0284c7", width=160).pack(side="left", padx=6)
        self.api_status_lbl = self._make_label(page, "本地 API (127.0.0.1:8787): 未启动", font=("Segoe UI", 11), color=FG_MUTED, bg=BG_DARK)
        self.api_status_lbl.pack(anchor="w", padx=12, pady=6)
        return page

    def _save_model_env(self):
        updates = {
            "IA_PROVIDER": self.prov_var.get(),
            "OPENAI_BASE_URL": self.base_url_var.get().strip(),
            "OPENAI_API_KEY": self.api_key_var.get().strip(),
            "IA_MODEL": self.model_var.get().strip(),
        }
        try:
            if env_config and hasattr(env_config, "save_env"):
                env_config.save_env(updates)
            else:
                for k, v in updates.items():
                    os.environ[k] = v
            messagebox.showinfo("成功", "模型与 API 配置已保存。")
        except Exception as exc:
            messagebox.showerror("错误", f"保存失败: {exc}")

    def _start_local_api(self):
        try:
            subprocess.Popen([sys.executable, os.path.join(ROOT, "launcher.py"), "--mode", "api"], cwd=ROOT)
            self.api_status_lbl.configure(text="本地 API (127.0.0.1:8787): 已尝试后台启动", color=SUCCESS if HAS_CTK else None)
        except Exception as exc:
            self.api_status_lbl.configure(text=f"启动失败: {exc}")

    def _build_updates_page(self):
        page = self._make_frame(self.container, bg=BG_DARK)
        hdr = self._make_frame(page, bg=BG_PANEL)
        hdr.pack(fill="x", padx=4, pady=(0, 8))
        self._make_label(hdr, f"🔄 自动更新与 Web 工作台 (当前版本 v{APP_VERSION})", font=("Segoe UI", 15, "bold"), color=ACCENT, bg=BG_PANEL).pack(side="left", padx=12, pady=8)

        self.update_info_lbl = self._make_label(page, f"当前运行版本: v{APP_VERSION}", font=("Segoe UI", 12), color=FG_TEXT, bg=BG_DARK)
        self.update_info_lbl.pack(anchor="w", padx=14, pady=10)

        row = self._make_frame(page, bg=BG_DARK)
        row.pack(anchor="w", padx=14, pady=8)
        self._make_button(row, "检查 GitHub 最新版本", self._check_updates, bg="#0284c7", width=180).pack(side="left", padx=6)
        self._make_button(row, "立即下载并升级", self._do_upgrade, bg="#059669", width=160).pack(side="left", padx=6)
        self._make_button(row, "一键启动原版 Streamlit (app.py)", self._launch_streamlit, bg="#7c3aed", width=230).pack(side="left", padx=6)
        return page

    def _check_updates(self):
        if updater is None:
            self.update_info_lbl.configure(text="updater 模块不可用")
            return
        try:
            info = updater.check_for_update()
            self.update_info_lbl.configure(text=f"更新检查结果: {info}")
        except Exception as exc:
            self.update_info_lbl.configure(text=f"检查更新失败: {exc}")

    def _do_upgrade(self):
        if updater is None:
            return
        try:
            res = updater.download_and_apply() if hasattr(updater, "download_and_apply") else "请前往 GitHub Releases 下载"
            messagebox.showinfo("升级结果", str(res))
        except Exception as exc:
            messagebox.showerror("升级失败", str(exc))

    def _launch_streamlit(self):
        try:
            subprocess.Popen([sys.executable, "-m", "streamlit", "run", os.path.join(ROOT, "app.py")], cwd=ROOT)
            webbrowser.open("http:" + "//localhost:8501")
        except Exception as exc:
            messagebox.showerror("启动失败", str(exc))

    def run(self):
        self.root.mainloop()


def main():
    app = InvestmentAgentGUI()
    app.run()


if __name__ == "__main__":
    main()

        
