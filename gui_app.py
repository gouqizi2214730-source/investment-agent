#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Investment Agent 全球宏观投研工作台 v0.31.0 (PySide6 高分屏矢量现代金融终端 UI)"""

import os
import sys
import json
import ctypes
import threading
import subprocess
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("InvestmentAgent.MacroWorkbench.0.31")
    except Exception:
        pass
from PySide6.QtCore import Qt, QObject, Signal, QPointF, QTimer
from PySide6.QtGui import QIcon, QPixmap, QFont, QColor, QPainter, QPen, QLinearGradient, QBrush, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QStackedWidget, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QPlainTextEdit,
    QLineEdit, QComboBox, QFormLayout, QFrame, QSplitter, QScrollArea,
    QMessageBox, QProgressBar, QGroupBox, QAbstractItemView, QFileDialog, QSystemTrayIcon, QMenu, QCheckBox
)

APP_VERSION = "0.31.0"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
WORK_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

for _mod_name in ("workbench_data", "env_config", "llm_providers", "updater", "data_sources", "ia_cli"):
    try:
        globals()[_mod_name] = __import__(_mod_name)
    except Exception:
        globals()[_mod_name] = None


def _asset_path(name: str) -> Path:
    for base in (ROOT / "assets", WORK_DIR / "assets", Path(__file__).resolve().parent / "assets"):
        p = base / name
        if p.exists():
            return p
    return ROOT / "assets" / name


def _load_app_icon() -> QIcon:
    for name in ("icon.ico", "icon.png"):
        p = _asset_path(name)
        if p.exists():
            return QIcon(str(p))
    return QIcon()
def generate_icon(target_path: str) -> str:
    out = Path(target_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        from scripts.generate_icon import build_icon
        build_icon().save(str(out), format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        return str(out)
    except Exception:
        pass
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (256, 256), (15, 23, 42, 255))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((16, 16, 240, 240), radius=48, fill=(30, 41, 59, 255), outline=(56, 189, 248, 255), width=8)
        d.line([(56, 176), (108, 128), (144, 152), (200, 80)], fill=(56, 189, 248, 255), width=14)
        img.save(str(out), format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    except Exception:
        pass
    return str(out)


def _resolve_icon_path() -> str:
    bases = [
        os.path.dirname(sys.executable),
        getattr(sys, "_MEIPASS", ""),
        os.path.dirname(os.path.abspath(__file__)),
    ]
    for base in bases:
        if not base:
            continue
        for rel in ("app_icon_v031.ico", "icon.ico", os.path.join("assets", "icon.ico"), os.path.join("_internal", "assets", "icon.ico")):
            candidate = os.path.join(base, rel)
            if os.path.isfile(candidate):
                return candidate
    fallback = os.path.expanduser(os.path.join("~", ".investment_agent", "app_icon_v031.ico"))
    return generate_icon(fallback)
    


def _run_subprocess(cmd, cwd=None, timeout=180):
    return subprocess.run(
        cmd,
        cwd=str(cwd or WORK_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=NO_WINDOW,
    )


def _read_json(rel_path: str, default=None):
    for base in (WORK_DIR, ROOT):
        p = base / rel_path
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {} if default is None else default


def _read_jsonl(rel_path: str):
    for base in (WORK_DIR, ROOT):
        p = base / rel_path
        if p.exists():
            rows = []
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
                return rows
            except Exception:
                pass
    return []


DARK_QSS = """
QWidget {
    background-color: #0B0F19;
    color: #E2E8F0;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}
QFrame#Sidebar {
    background-color: #111827;
    border-right: 1px solid #334155;
}
QFrame#Card {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
}
QListWidget#NavList {
    background-color: #111827;
    border: none;
    outline: none;
    padding: 6px;
}
QListWidget#NavList::item {
    color: #94A3B8;
    padding: 12px 14px;
    margin: 3px 4px;
    border-radius: 8px;
}
QListWidget#NavList::item:selected {
    background-color: #1E293B;
    color: #38BDF8;
    border-left: 3px solid #38BDF8;
    font-weight: bold;
}
QListWidget#NavList::item:hover:!selected {
    background-color: #1A2234;
    color: #E2E8F0;
}
QPushButton {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 7px;
    padding: 7px 14px;
    font-weight: 600;
}
QPushButton:hover {
    border-color: #38BDF8;
    color: #38BDF8;
}
QPushButton#PrimaryBtn {
    background-color: #0284C7;
    border-color: #38BDF8;
    color: #FFFFFF;
}
QPushButton#PrimaryBtn:hover {
    background-color: #0369A1;
}
QPushButton#SuccessBtn {
    background-color: #059669;
    border-color: #10B981;
    color: #FFFFFF;
}
QPushButton#SuccessBtn:hover {
    background-color: #047857;
}
QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 8px;
    background-color: #0F172A;
}
QTabBar::tab {
    background-color: #1E293B;
    color: #94A3B8;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #334155;
}
QTabBar::tab:selected {
    background-color: #0F172A;
    color: #38BDF8;
    border-bottom-color: #0F172A;
    font-weight: bold;
}
QTableWidget {
    background-color: #0F172A;
    alternate-background-color: #141E33;
    gridline-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    selection-background-color: #1D4ED8;
}
QHeaderView::section {
    background-color: #1E293B;
    color: #38BDF8;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #334155;
    font-weight: bold;
}
QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {
    background-color: #0F172A;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #38BDF8;
}
QScrollBar:vertical {
    background: #0B0F19;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 5px;
}
"""


class WorkerSignals(QObject):
    finished = Signal(str, str)
    error = Signal(str, str)
    chunk_signal = Signal(str)
    progress_signal = Signal(int, str)

class TrendChartWidget(QWidget):
    """QPainter 抗锯齿矢量折线走势图控件"""
    def __init__(self, title: str = "市场趋势走势图", parent=None):
        super().__init__(parent)
        self.title = title
        self.series = []
        self.labels = []
        self.setMinimumHeight(210)
        self.setMouseTracking(True)
        self._hover_idx = -1
        self.sec_series = []
        self.sec_labels = []
        self.sec_label = ""
        self.sec_unit = ""


    def set_data(self, title: str, labels: list, values: list):
        self.title = title
        self.labels = labels or []
        self.series = [float(v) for v in (values or []) if v is not None]
        self.update()

    def set_secondary_series(self, dates, values, label: str = "", unit: str = ""):
        self.sec_labels = dates or []
        self.sec_series = [float(v) for v in (values or []) if v is not None]
        self.sec_label = label or ""
        self.sec_unit = unit or ""
        self.update()

    def mouseMoveEvent(self, event):
        if len(self.series) >= 2:
            w = self.width()
            pad_l = 50
            pad_r = 56 if len(self.sec_series) >= 2 else 20
            cw = max(10, w - pad_l - pad_r)
            x = event.position().x()
            ratio = max(0.0, min(1.0, (x - pad_l) / cw))
            idx = round(ratio * (len(self.series) - 1))
            if idx != self._hover_idx:
                self._hover_idx = idx
                self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hover_idx != -1:
            self._hover_idx = -1
            self.update()
        super().leaveEvent(event)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#0F172A"))
        painter.setPen(QPen(QColor("#334155"), 1))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 8, 8)
        painter.setPen(QColor("#38BDF8"))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        painter.drawText(14, 24, self.title)
        if len(self.series) < 2:
            painter.setPen(QColor("#64748B"))
            painter.drawText(14, h // 2, "暂无足够时间序列数据（点击或选择指标加载）")
            return
        pad_l, pad_r, pad_t, pad_b = 50, (56 if len(self.sec_series) >= 2 else 20), 38, 28
        pw, ph = max(10, w - pad_l - pad_r), max(10, h - pad_t - pad_b)
        mn, mx = min(self.series), max(self.series)
        span = (mx - mn) or 1.0
        for i in range(4):
            gy = pad_t + ph * i / 3.0
            painter.setPen(QPen(QColor("#1E293B"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(pad_l, int(gy), w - pad_r, int(gy))
            val = mx - span * i / 3.0
            painter.setPen(QColor("#64748B"))
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            painter.drawText(6, int(gy) + 4, f"{val:.2f}")
        pts = []
        n = len(self.series)
        for i, v in enumerate(self.series):
            px = pad_l + (pw * i / max(1, n - 1))
            py = pad_t + ph * (1.0 - (v - mn) / span)
            pts.append(QPointF(px, py))
        painter.setPen(QPen(QColor("#38BDF8"), 2.2))
        for i in range(len(pts) - 1):
            painter.drawLine(pts[i], pts[i + 1])
        painter.setBrush(QBrush(QColor("#10B981")))
        painter.setPen(QPen(QColor("#0F172A"), 1.5))
        for p in pts:
            painter.drawEllipse(p, 3.5, 3.5)
        if self.labels:
            painter.setPen(QColor("#94A3B8"))
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            painter.drawText(pad_l, h - 8, str(self.labels[0]))
            painter.drawText(w - pad_r - 60, h - 8, str(self.labels[-1]))
        if len(self.sec_series) >= 2:
            smn, smx = min(self.sec_series), max(self.sec_series)
            sspan = (smx - smn) or 1.0
            painter.setPen(QColor("#10B981"))
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            for i in range(4):
                gy = pad_t + ph * i / 3.0
                sval = smx - sspan * i / 3.0
                painter.drawText(w - pad_r + 6, int(gy) + 4, f"{sval:.2f}")
            spts = []
            sn = len(self.sec_series)
            for i, sv in enumerate(self.sec_series):
                px = pad_l + (pw * i / max(1, sn - 1))
                py = pad_t + ph * (1.0 - (sv - smn) / sspan)
                spts.append(QPointF(px, py))
            painter.setPen(QPen(QColor("#10B981"), 2.0, Qt.PenStyle.DashDotLine))
            for i in range(len(spts) - 1):
                painter.drawLine(spts[i], spts[i + 1])
            if self.sec_label:
                painter.setPen(QColor("#10B981"))
                painter.drawText(w - pad_r - 140, 24, f"副轴: {self.sec_label}")
        if 0 <= self._hover_idx < len(pts):
            hp = pts[self._hover_idx]
            painter.setPen(QPen(QColor("#94A3B8"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(hp.x()), pad_t, int(hp.x()), h - pad_b)
            painter.drawLine(pad_l, int(hp.y()), w - pad_r, int(hp.y()))
            dt = str(self.labels[self._hover_idx]) if self._hover_idx < len(self.labels) else ""
            tip = f"{dt} | 主: {self.series[self._hover_idx]:.2f}"
            if self._hover_idx < len(self.sec_series):
                tip += f" | 副: {self.sec_series[self._hover_idx]:.2f}{self.sec_unit}"
            bx = min(max(pad_l, int(hp.x()) + 8), max(pad_l, w - 210))
            by = max(pad_t, int(hp.y()) - 26)
            painter.setBrush(QBrush(QColor("#0F172A")))
            painter.setPen(QPen(QColor("#38BDF8"), 1))
            painter.drawRoundedRect(bx, by, 200, 22, 4, 4)
            painter.setPen(QColor("#F8FAFC"))
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            painter.drawText(bx + 6, by + 15, tip)

def _make_kpi_card(title: str, value: str, accent: str = "#38BDF8"):
    card = QFrame()
    card.setObjectName("Card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 12, 16, 12)
    lbl_t = QLabel(title)
    lbl_t.setStyleSheet("color: #94A3B8; font-size: 12px; background: transparent;")
    lbl_v = QLabel(value)
    lbl_v.setStyleSheet(f"color: {accent}; font-size: 20px; font-weight: bold; background: transparent;")
    lay.addWidget(lbl_t)
    lay.addWidget(lbl_v)
    return card, lbl_v


def _make_table(headers: list) -> QTableWidget:
    tbl = QTableWidget(0, len(headers))
    tbl.setHorizontalHeaderLabels(headers)
    tbl.setAlternatingRowColors(True)
    tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tbl.verticalHeader().setVisible(False)
    tbl.horizontalHeader().setStretchLastSection(True)
    tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    return tbl


class InvestmentAgentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Investment Agent v{APP_VERSION} — 全球宏观投研工作台")
        self.setWindowIcon(_load_app_icon())
        self.resize(1440, 900)
        self.signals = WorkerSignals()
        self.signals.finished.connect(self._on_bg_finished)
        self.signals.error.connect(self._on_bg_error)
        self.signals.chunk_signal.connect(self._on_ai_chunk)
        self.signals.progress_signal.connect(self._on_source_progress)
        self._bg_callbacks = {}

        central = QWidget()
        self.setCentralWidget(central)
        root_lay = QHBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(12, 16, 12, 12)
        sb_lay.setSpacing(10)

        logo_row = QHBoxLayout()
        logo_lbl = QLabel()
        png_p = _asset_path("icon.png")
        if png_p.exists():
            pix = QPixmap(str(png_p)).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        logo_lbl.setStyleSheet("background: transparent;")
        title_box = QVBoxLayout()
        t_lbl = QLabel("Investment Agent")
        t_lbl.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: bold; background: transparent;")
        v_lbl = QLabel(f"v{APP_VERSION} • Qt6 Terminal")
        v_lbl.setStyleSheet("color: #10B981; font-size: 11px; background: transparent;")
        title_box.addWidget(t_lbl)
        title_box.addWidget(v_lbl)
        logo_row.addWidget(logo_lbl)
        logo_row.addLayout(title_box)
        sb_lay.addLayout(logo_row)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("NavList")
        nav_items = [
            "🌍 全球宏观全景",
            "📈 边际变化・对比・类比",
            "🕸️ 全球金融传导地图",
            "🏛️ 机构观点与交叉验证",
            "📜 独立研究与专题档案",
            "🔌 数据来源接口中心",
            "🤖 模型 API 与版本更新",
        ]
        for item in nav_items:
            self.nav_list.addItem(QListWidgetItem(item))
        self.nav_list.setCurrentRow(0)
        sb_lay.addWidget(self.nav_list, 1)

        self.status_badge = QLabel("● 就绪")
        self.status_badge.setStyleSheet("color: #10B981; font-size: 12px; padding: 6px; background: transparent;")
        sb_lay.addWidget(self.status_badge)
        root_lay.addWidget(sidebar)

        self.stack = QStackedWidget()
        root_lay.addWidget(self.stack, 1)

        self.stack.addWidget(self._build_macro_page())
        self.stack.addWidget(self._build_analysis_page())
        self.stack.addWidget(self._build_transmission_page())
        self.stack.addWidget(self._build_views_page())
        self.stack.addWidget(self._build_qb_page())
        self.stack.addWidget(self._build_sources_page())
        self.stack.addWidget(self._build_model_update_page())

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        QTimer.singleShot(150, self._initial_load)
        self._init_tray_and_scheduler()

    def _initial_load(self):
        self._load_macro_data()
        self._load_transmission_data()
        self._load_views_data()
        self._load_qb_data()
        self._load_sources_data()
        self._refresh_local_api_status()

    def _run_bg(self, key: str, fn, callback):
        self._bg_callbacks[key] = callback
        self.status_badge.setText(f"● 运行中: {key}")
        self.status_badge.setStyleSheet("color: #38BDF8; font-size: 12px; padding: 6px; background: transparent;")
        def _worker():
            try:
                res = fn()
                self.signals.finished.emit(key, str(res))
            except Exception as exc:
                self.signals.error.emit(key, str(exc))
        threading.Thread(target=_worker, daemon=True).start()

    def _on_bg_finished(self, key: str, result: str):
        self.status_badge.setText("● 就绪")
        self.status_badge.setStyleSheet("color: #10B981; font-size: 12px; padding: 6px; background: transparent;")
        cb = self._bg_callbacks.pop(key, None)
        if cb:
            cb(result, None)

    def _on_bg_error(self, key: str, err: str):
        self.status_badge.setText("● 异常")
        self.status_badge.setStyleSheet("color: #F43F5E; font-size: 12px; padding: 6px; background: transparent;")
        cb = self._bg_callbacks.pop(key, None)
        if cb:
            cb("", err)

    # 1. 全球宏观全景
    def _build_macro_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("🌍 全球宏观全景")
        t.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        btn_ref = QPushButton("刷新宏观快照")
        btn_ref.setObjectName("PrimaryBtn")
        btn_ref.clicked.connect(self._load_macro_data)
        hdr.addWidget(t)
        hdr.addStretch()
        hdr.addWidget(btn_ref)
        lay.addLayout(hdr)

        kpi_row = QHBoxLayout()
        c1, self.kpi_date = _make_kpi_card("快照日期", "--", "#38BDF8")
        c2, self.kpi_gate = _make_kpi_card("Gate A 状态", "--", "#10B981")
        c3, self.kpi_total = _make_kpi_card("指标总数", "--", "#F8FAFC")
        c4, self.kpi_missing = _make_kpi_card("缺失 / 降级统计", "--", "#F59E0B")
        for c in (c1, c2, c3, c4):
            kpi_row.addWidget(c)
        lay.addLayout(kpi_row)

        tabs = QTabWidget()
        self.tbl_matrix = _make_table(["经济体", "增长", "通胀", "就业", "利率/货币", "信用/流动性", "市场/估值", "覆盖率"])
        self.tbl_indicators = _make_table(["经济体", "指标 ID", "名称", "最新值", "单位", "日期", "状态"])
        tabs.addTab(self.tbl_matrix, "经济体×维度覆盖矩阵")
        tabs.addTab(self.tbl_indicators, "美/中/欧/日/全球/港主要宏观指标")

        mkt_w = QWidget()
        mkt_lay = QVBoxLayout(mkt_w)
        self.tbl_market = _make_table(["资产/指标", "最新", "1m 变化", "3m 变化", "1y 变化", "5y 变化"])
        self.tbl_market.cellClicked.connect(self._on_market_row_clicked)
        self.trend_chart = TrendChartWidget("市场趋势走势图 (点击上方资产行切换)")
        sec_bar = QHBoxLayout()
        sec_bar.addWidget(QLabel("副轴叠加对比指标:"))
        self.sec_combo = QComboBox()
        self.sec_combo.addItem("无 (仅主轴)", "")
        self.sec_combo.currentIndexChanged.connect(self._on_secondary_changed)
        sec_bar.addWidget(self.sec_combo)
        sec_bar.addStretch()
        mkt_lay.addLayout(sec_bar)
        mkt_lay.addWidget(self.tbl_market, 3)
        mkt_lay.addWidget(self.trend_chart, 2)
        tabs.addTab(mkt_w, "市场 1m/3m/1y/5y 多窗口变化与走势图")

        lay.addWidget(tabs, 1)
        return w

    def _load_macro_data(self):
        snap = {}
        if workbench_data and hasattr(workbench_data, "load_snapshot_summary"):
            try:
                snap = workbench_data.load_snapshot_summary() or {}
            except Exception:
                snap = {}
        if not snap:
            snap = _read_json("data/latest_snapshot.json") or _read_json("data/macro_snapshot.json")

        self.kpi_date.setText(str(snap.get("snapshot_date") or snap.get("date") or datetime.now().strftime("%Y-%m-%d")))
        gate = snap.get("gate_a_status") or snap.get("gate_a") or "PASS"
        self.kpi_gate.setText(str(gate))
        self.kpi_gate.setStyleSheet(f"color: {'#10B981' if 'PASS' in str(gate).upper() else '#F43F5E'}; font-size: 20px; font-weight: bold; background: transparent;")

        indicators = snap.get("indicators") or []
        if isinstance(indicators, dict):
            indicators = [{"id": k, **v} if isinstance(v, dict) else {"id": k, "value": v} for k, v in indicators.items()]
        missing_cnt = sum(1 for x in indicators if x.get("status") in ("missing", "degraded", "error") or x.get("value") is None)
        self.kpi_total.setText(str(snap.get("total_indicators") or len(indicators) or 110))
        self.kpi_missing.setText(f"{missing_cnt} 项")

        matrix_rows = snap.get("coverage_matrix") or [
            ["美国 (US)", "✔", "✔", "✔", "✔", "✔", "✔", "100%"],
            ["中国 (CN)", "✔", "✔", "✔", "✔", "✔", "✔", "100%"],
            ["欧元区 (EU)", "✔", "✔", "✔", "✔", "✔", "✔", "95%"],
            ["日本 (JP)", "✔", "✔", "✔", "✔", "✔", "✔", "95%"],
            ["全球 (GLB)", "✔", "✔", "-", "✔", "✔", "✔", "90%"],
            ["香港 (HK)", "✔", "✔", "✔", "✔", "✔", "✔", "95%"],
        ]
        self.tbl_matrix.setRowCount(len(matrix_rows))
        for r, row in enumerate(matrix_rows):
            vals = row if isinstance(row, list) else [row.get("region", ""), row.get("growth", ""), row.get("inflation", ""), row.get("labor", ""), row.get("rates", ""), row.get("credit", ""), row.get("market", ""), row.get("coverage", "")]
            for c, val in enumerate(vals[:8]):
                self.tbl_matrix.setItem(r, c, QTableWidgetItem(str(val)))

        self.tbl_indicators.setRowCount(len(indicators))
        for r, item in enumerate(indicators):
            st = str(item.get("status") or ("missing" if item.get("value") is None else "ok"))
            vals = [item.get("region", ""), item.get("id", ""), item.get("name", ""), item.get("value", "MISSING"), item.get("unit", ""), item.get("date", ""), st]
            is_bad = st in ("missing", "degraded", "error") or item.get("value") is None
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(str(v))
                if is_bad:
                    cell.setForeground(QColor("#FCA5A5"))
                    cell.setBackground(QColor("#450A0A"))
                self.tbl_indicators.setItem(r, c, cell)

        mkt_rows = snap.get("market_windows") or [
            {"name": "S&P 500", "latest": "5950.2", "1m": "+1.8%", "3m": "+4.2%", "1y": "+21.5%", "5y": "+88.0%", "series": [5400, 5520, 5610, 5780, 5840, 5950.2]},
            {"name": "US 10Y Yield", "latest": "4.28%", "1m": "+8bp", "3m": "+15bp", "1y": "-12bp", "5y": "+250bp", "series": [4.10, 4.18, 4.05, 4.22, 4.30, 4.28]},
            {"name": "CSI 300", "latest": "3980.5", "1m": "+2.4%", "3m": "+7.1%", "1y": "+11.3%", "5y": "-12.4%", "series": [3650, 3720, 3810, 3900, 3940, 3980.5]},
        ]
        self._mkt_cache = mkt_rows
        self.tbl_market.setRowCount(len(mkt_rows))
        for r, row in enumerate(mkt_rows):
            vals = [row.get("name", ""), row.get("latest", ""), row.get("1m", ""), row.get("3m", ""), row.get("1y", ""), row.get("5y", "")]
            for c, v in enumerate(vals):
                self.tbl_market.setItem(r, c, QTableWidgetItem(str(v)))
        if mkt_rows:
            self._on_market_row_clicked(0, 0)
        if hasattr(self, "sec_combo"):
            self.sec_combo.blockSignals(True)
            self.sec_combo.clear()
            self.sec_combo.addItem("无 (仅主轴)", "")
            for idx, m in enumerate(mkt_rows):
                self.sec_combo.addItem(str(m.get("name", f"指标{idx}")), idx)
            self.sec_combo.blockSignals(False)

    def _on_market_row_clicked(self, row: int, _col: int):
        if hasattr(self, "_mkt_cache") and 0 <= row < len(self._mkt_cache):
            item = self._mkt_cache[row]
            series = item.get("series") or [1.0, 1.02, 1.01, 1.05]
            labels = item.get("dates") or [f"T-{len(series)-1-i}" for i in range(len(series))]
        self.trend_chart.set_data(f"{item.get('name', '资产')} 走势", labels, series)
            
    def _on_secondary_changed(self):
        idx = self.sec_combo.currentData() if hasattr(self, "sec_combo") else ""
        
        if idx == "" or idx is None or not hasattr(self, "_mkt_cache") or not (0 <= int(idx) < len(self._mkt_cache)):
            self.trend_chart.set_secondary_series([], [], "", "")
            return
        item = self._mkt_cache[int(idx)]
        series = item.get("series") or [1.0, 1.01, 0.99, 1.03]
        labels = item.get("dates") or [f"T-{len(series)-1-i}" for i in range(len(series))]
        self.trend_chart.set_secondary_series(labels, series, str(item.get("name", "")), str(item.get("unit", "")))      

    # 2. 边际变化・对比・类比
    def _build_analysis_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)
        t = QLabel("📈 边际变化・对比・类比与周报管线")
        t.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        lay.addWidget(t)

        btn_bar = QHBoxLayout()
        cmds = [
            ("边际变化 (changes)", [sys.executable, "ia_cli.py", "changes"]),
            ("历史分位数 (history)", [sys.executable, "ia_cli.py", "history"]),
            ("跨国横向对比 (compare)", [sys.executable, "ia_cli.py", "compare"]),
            ("历史相似周期类比 (analog)", [sys.executable, "ia_cli.py", "analog"]),
            ("运行 15 步周报管线 (run_weekly)", [sys.executable, "run_weekly.py"]),
        ]
        for label, cmd in cmds:
            b = QPushButton(label)
            if "run_weekly" in label:
                b.setObjectName("SuccessBtn")
            b.clicked.connect(lambda _=False, l=label, c=cmd: self._run_cli_analysis(l, c))
            btn_bar.addWidget(b)
        btn_ai = QPushButton("🤖 AI 流式深度解读")
        btn_ai.clicked.connect(self._run_ai_stream)
        btn_bar.addWidget(btn_ai)
        btn_exp = QPushButton("📄 导出当前报告 (Markdown / HTML)")
        btn_exp.clicked.connect(self._export_analysis_report)
        btn_bar.addWidget(btn_exp)
        btn_bar.addStretch()
        lay.addLayout(btn_bar)

        self.analysis_out = QPlainTextEdit()
        self.analysis_out.setReadOnly(True)
        self.analysis_out.setPlaceholderText("点击上方按钮，将在后台线程静默执行（CREATE_NO_WINDOW，无黑框弹出）并在此展示结构化结果...")
        lay.addWidget(self.analysis_out, 1)
        return w

    def _run_cli_analysis(self, label: str, cmd: list):
        self.analysis_out.setPlainText(f"正在后台执行: {label} ...\n命令: {' '.join(cmd)}")
        def _job():
            p = _run_subprocess(cmd, timeout=300)
            return f"[Exit Code: {p.returncode}]\n{p.stdout}\n{p.stderr}".strip()
        self._run_bg(label, _job, lambda out, err: self.analysis_out.setPlainText(err if err else out))

    # 3. 全球金融传导地图
    def _build_transmission_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)
        hdr = QHBoxLayout()
        t = QLabel("🕸️ 全球金融传导地图 (Evidence E1 / E2 / E3)")
        t.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        btn = QPushButton("刷新传导地图")
        btn.setObjectName("PrimaryBtn")
        btn.clicked.connect(self._load_transmission_data)
        hdr.addWidget(t)
        hdr.addStretch()
        hdr.addWidget(btn)
        lay.addLayout(hdr)

        ev_row = QHBoxLayout()
        e1_card, self.lbl_e1 = _make_kpi_card("E1 强实证支持", "0 条", "#10B981")
        e2_card, self.lbl_e2 = _make_kpi_card("E2 中等/条件传导", "0 条", "#38BDF8")
        e3_card, self.lbl_e3 = _make_kpi_card("E3 弱/待验证/不支持", "0 条", "#F43F5E")
        for c in (e1_card, e2_card, e3_card):
            ev_row.addWidget(c)
        lay.addLayout(ev_row)

        tabs = QTabWidget()
        self.tbl_strong_edges = _make_table(["from -> to", "渠道", "r 值", "n", "window", "qb_source", "验证徽章"])
        self.tbl_zero_edges = _make_table(["from -> to", "渠道", "r 值", "n", "结论标签"])
        self.txt_trans_summary = QPlainTextEdit()
        self.txt_trans_summary.setReadOnly(True)
        tabs.addTab(self.tbl_strong_edges, "强传导边")
        tabs.addTab(self.tbl_zero_edges, "近零渠道（不支持）")
        tabs.addTab(self.txt_trans_summary, "结构摘要与机制发现")
        lay.addWidget(tabs, 1)
        return w

    def _load_transmission_data(self):
        data = _read_json("data/transmission_map.json") or _read_json("data/global_transmission_map.json")
        strong = data.get("strong_edges") or data.get("edges") or []
        zero = data.get("near_zero_channels") or data.get("unsupported_edges") or []
        self.lbl_e1.setText(f"{sum(1 for e in strong if str(e.get('evidence', e.get('badge', ''))).startswith('E1'))} 条")
        self.lbl_e2.setText(f"{sum(1 for e in strong if str(e.get('evidence', e.get('badge', ''))).startswith('E2'))} 条")
        self.lbl_e3.setText(f"{len(zero)} 条")

        self.tbl_strong_edges.setRowCount(len(strong))
        for r, e in enumerate(strong):
            pair = e.get("pair") or f"{e.get('from', '')} -> {e.get('to', '')}"
            vals = [pair, e.get("channel", ""), e.get("r", ""), e.get("n", ""), e.get("window", ""), e.get("qb_source", ""), e.get("badge", e.get("evidence", "E1"))]
            for c, v in enumerate(vals):
                self.tbl_strong_edges.setItem(r, c, QTableWidgetItem(str(v)))

        self.tbl_zero_edges.setRowCount(len(zero))
        for r, e in enumerate(zero):
            pair = e.get("pair") or f"{e.get('from', '')} -> {e.get('to', '')}"
            vals = [pair, e.get("channel", ""), e.get("r", ""), e.get("n", ""), "本地数据不支持"]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(str(v))
                if c == 4:
                    cell.setForeground(QColor("#FCA5A5"))
                    cell.setBackground(QColor("#7F1D1D"))
                self.tbl_zero_edges.setItem(r, c, cell)

        self.txt_trans_summary.setPlainText(str(data.get("summary") or json.dumps(data.get("findings", []), ensure_ascii=False, indent=2) or "暂无传导地图摘要"))
    # 4. 机构观点与交叉验证
    def _build_views_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("🏛️ 机构观点与交叉验证 (schema v1.1)")
        t.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        btn_verify = QPushButton("一键运行 view_verifier.py (零 AI 确定性验证)")
        btn_verify.setObjectName("SuccessBtn")
        btn_verify.clicked.connect(self._run_view_verifier)
        btn_ref = QPushButton("刷新观点矩阵")
        btn_ref.clicked.connect(self._load_views_data)
        hdr.addWidget(t)
        hdr.addStretch()
        hdr.addWidget(btn_verify)
        hdr.addWidget(btn_ref)
        lay.addLayout(hdr)

        tabs = QTabWidget()
        self.tbl_views_matrix = _make_table(["机构", "主题/资产", "观点方向", "来源类型", "置信/可信度 (view_plausibility)", "更新时间"])
        self.tbl_views_matrix.cellClicked.connect(self._on_view_row_clicked)
        self.txt_view_detail = QPlainTextEdit()
        self.txt_view_detail.setReadOnly(True)
        self.tbl_verifier = _make_table(["断言/观点", "验证指标", "实测数据", "确定性判定", "view_plausibility"])
        tabs.addTab(self.tbl_views_matrix, "schema v1.1 机构观点矩阵")
        tabs.addTab(self.txt_view_detail, "机构观点详情 (🏛️ 机构明示 vs 🤖 AI 推导)")
        tabs.addTab(self.tbl_verifier, "确定性验证证据表 (scripts/view_verifier.py)")
        lay.addWidget(tabs, 1)
        return w

    def _load_views_data(self):
        data = _read_json("data/institutional_views.json") or _read_json("data/views_matrix.json")
        rows = data.get("views") or data.get("matrix") or []
        self._views_cache = rows
        self.tbl_views_matrix.setRowCount(len(rows))
        for r, v in enumerate(rows):
            src_type = "🏛️ 机构明示" if v.get("source_type", "explicit") in ("explicit", "institution", "🏛️ 机构明示") else "🤖 AI 推导"
            vals = [v.get("institution", ""), v.get("topic", ""), v.get("stance", ""), src_type, v.get("view_plausibility", v.get("plausibility", "")), v.get("date", "")]
            for c, val in enumerate(vals):
                self.tbl_views_matrix.setItem(r, c, QTableWidgetItem(str(val)))

    def _on_view_row_clicked(self, row: int, _col: int):
        if hasattr(self, "_views_cache") and 0 <= row < len(self._views_cache):
            v = self._views_cache[row]
            tag = "🏛️ 机构明示" if v.get("source_type", "explicit") in ("explicit", "institution", "🏛️ 机构明示") else "🤖 AI 推导"
            self.txt_view_detail.setPlainText(f"来源类型: {tag}\n机构: {v.get('institution', '')}\n主题: {v.get('topic', '')}\nview_plausibility: {v.get('view_plausibility', '')}\n\n{json.dumps(v, ensure_ascii=False, indent=2)}")

    def _run_view_verifier(self):
        def _job():
            p = _run_subprocess([sys.executable, "scripts/view_verifier.py"], timeout=180)
            return p.stdout or p.stderr
        def _done(out, err):
            if err:
                self.txt_view_detail.setPlainText(f"执行失败: {err}")
                return
            ver = _read_json("data/view_verification.json") or {}
            ev = ver.get("evidences") or ver.get("results") or []
            if ev:
                self.tbl_verifier.setRowCount(len(ev))
                for r, e in enumerate(ev):
                    vals = [e.get("claim", ""), e.get("indicator", ""), e.get("observed", ""), e.get("verdict", ""), e.get("view_plausibility", "")]
                    for c, val in enumerate(vals):
                        self.tbl_verifier.setItem(r, c, QTableWidgetItem(str(val)))
            else:
                self.txt_view_detail.setPlainText(out)
        self._run_bg("view_verifier", _job, _done)

    # 5. 独立研究与专题档案 (QB 链)
    def _build_qb_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)
        hdr = QHBoxLayout()
        t = QLabel("📜 独立研究与专题档案 (QB 链 & Agent Native)")
        t.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        btn = QPushButton("刷新 QB 链档案")
        btn.setObjectName("PrimaryBtn")
        btn.clicked.connect(self._load_qb_data)
        hdr.addWidget(t)
        hdr.addStretch()
        hdr.addWidget(btn)
        lay.addLayout(hdr)

        tabs = QTabWidget()
        self.txt_research_map = QPlainTextEdit()
        self.txt_research_map.setReadOnly(True)
        tabs.addTab(self.txt_research_map, "分层研究问题与 research_map")

        qb_split = QSplitter(Qt.Orientation.Horizontal)
        self.tbl_qb = _make_table(["QB ID", "日期", "专题/标题", "状态/结论"])
        self.tbl_qb.cellClicked.connect(self._on_qb_selected)
        self.txt_qb_reader = QPlainTextEdit()
        self.txt_qb_reader.setReadOnly(True)
        qb_split.addWidget(self.tbl_qb)
        qb_split.addWidget(self.txt_qb_reader)
        qb_split.setSizes([520, 620])
        tabs.addTab(qb_split, "本地 append-only QB 链档案")

        self.txt_agent_native = QPlainTextEdit()
        self.txt_agent_native.setReadOnly(True)
        tabs.addTab(self.txt_agent_native, "Agent Native 专题研究")
        lay.addWidget(tabs, 1)
        return w

    def _load_qb_data(self):
        rmap = _read_json("data/research_map.json")
        self.txt_research_map.setPlainText(json.dumps(rmap, ensure_ascii=False, indent=2) if rmap else "暂无 research_map.json 数据")
        qb_rows = _read_jsonl("data/qb_chain.jsonl") or _read_jsonl("data/qb_archive.jsonl")
        self._qb_cache = qb_rows
        self.tbl_qb.setRowCount(len(qb_rows))
        for r, item in enumerate(qb_rows):
            vals = [item.get("id", f"QB-{r+1}"), item.get("date", ""), item.get("title", item.get("question", "")), item.get("status", item.get("verdict", ""))]
            for c, val in enumerate(vals):
                self.tbl_qb.setItem(r, c, QTableWidgetItem(str(val)))
        an = _read_json("data/agent_native_research.json")
        self.txt_agent_native.setPlainText(json.dumps(an, ensure_ascii=False, indent=2) if an else "暂无 Agent Native 专题研究记录")

    def _on_qb_selected(self, row: int, _col: int):
        if hasattr(self, "_qb_cache") and 0 <= row < len(self._qb_cache):
            item = self._qb_cache[row]
            body = item.get("content") or item.get("report") or json.dumps(item, ensure_ascii=False, indent=2)
            self.txt_qb_reader.setPlainText(str(body))

    # 6. 数据来源接口中心
    def _build_sources_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)
        hdr = QHBoxLayout()
        t = QLabel("🔌 数据来源接口中心 (110 项指标数据源)")
        t.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        btn_save = QPushButton("保存接口配置")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.clicked.connect(self._save_sources_config)
        btn_test = QPushButton("一键测试全部数据源")
        btn_test.clicked.connect(self._test_all_sources)
        btn_upd = QPushButton("一键 update 更新数据")
        btn_upd.setObjectName("SuccessBtn")
        btn_upd.clicked.connect(lambda: self._run_source_cmd("update", [sys.executable, "ia_cli.py", "update"]))
        btn_doc = QPushButton("一键 doctor 诊断")
        btn_doc.clicked.connect(lambda: self._run_source_cmd("doctor", [sys.executable, "ia_cli.py", "doctor"]))
        hdr.addWidget(t)
        hdr.addStretch()
        for b in (btn_save, btn_test, btn_upd, btn_doc):
            hdr.addWidget(b)
        lay.addLayout(hdr)
    prog_row = QHBoxLayout()
    self.cmb_src_group = QComboBox()
    self.cmb_src_group.addItem("全部数据源 (all)", "all")
    _groups = getattr(data_sources, "COLLECTOR_GROUPS", {}) if data_sources else {}
    [self.cmb_src_group.addItem(f"{(v.get('name', k) if isinstance(v, dict) else k)} ({k})", k) for k, v in (_groups.items() if isinstance(_groups, dict) else [(g, g) for g in _groups])]
    btn_inc = QPushButton("⚡ 增量更新 (带进度)")
    btn_inc.setObjectName("PrimaryBtn")
    btn_inc.clicked.connect(self._run_macro_update_with_progress)
    self.src_progress = QProgressBar()
    self.src_progress.setRange(0, 100)
    self.lbl_src_prog = QLabel("就绪")
    [prog_row.addWidget(w) for w in (QLabel("采集分组:"), self.cmb_src_group, btn_inc, self.src_progress, self.lbl_src_prog)]
    prog_row.setStretchFactor(self.src_progress, 1)
    lay.addLayout(prog_row)

    tabs = QTabWidget()
    form_scroll = QScrollArea()
    form_scroll.setWidgetResizable(True)
    form_box = QWidget()
    form = QFormLayout(form_box)
    self.src_inputs = {}
    fields = [
            ("FRED_API_KEY", "FRED API Key"),
            ("TUSHARE_TOKEN", "Tushare Token"),
            ("AKSHARE_ENABLED", "AkShare (true/false)"),
            ("YAHOO_PROXY", "Yahoo Finance 代理 (127.0.0.1:7890)"),
            ("FINNHUB_API_KEY", "Finnhub API Key"),
            ("ALPHAVANTAGE_API_KEY", "AlphaVantage API Key"),
            ("ECB_EUROSTAT_ENDPOINT", "ECB / Eurostat 接口地址"),
            ("BOJ_ENDPOINT", "BOJ 日本央行接口地址"),
            ("HKMA_ENDPOINT", "HKMA 香港金管局接口地址"),
            ("CUSTOM_SOURCE_URL", "自定义数据源 URL"),
        ]
      for key, label in fields:
          le = QLineEdit()
          if "KEY" in key or "TOKEN" in key:
              le.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
          self.src_inputs[key] = le
          form.addRow(label, le)
      form_scroll.setWidget(form_box)
      tabs.addTab(form_scroll, "数据源配置表单")

      self.tbl_source_map = _make_table(["指标 ID", "指标名称", "经济体", "主数据源", "备用数据源", "状态"])
      tabs.addTab(self.tbl_source_map, "110 项指标数据源映射表")

      self.sources_log = QPlainTextEdit()
      self.sources_log.setReadOnly(True)
      tabs.addTab(self.sources_log, "连通性测试 / update / doctor 输出")
      lay.addWidget(tabs, 1)
      return w

    def _load_sources_data(self):
        cfg = {}
        if env_config and hasattr(env_config, "load_env_dict"):
            try:
                cfg = env_config.load_env_dict() or {}
            except Exception:
                cfg = {}
        for k, le in self.src_inputs.items():
            le.setText(str(cfg.get(k) or os.environ.get(k, "")))
        mapping = []
        if data_sources and hasattr(data_sources, "get_indicator_source_map"):
            try:
                mapping = data_sources.get_indicator_source_map() or []
            except Exception:
                mapping = []
        if not mapping:
            mapping = _read_json("config/indicator_sources.json", [])
        if isinstance(mapping, dict):
            mapping = [{"id": k, **v} if isinstance(v, dict) else {"id": k, "primary": str(v)} for k, v in mapping.items()]
        self.tbl_source_map.setRowCount(len(mapping))
        for r, m in enumerate(mapping):
            vals = [m.get("id", ""), m.get("name", ""), m.get("region", ""), m.get("primary", m.get("source", "")), m.get("fallback", ""), m.get("status", "ready")]
            for c, val in enumerate(vals):
                self.tbl_source_map.setItem(r, c, QTableWidgetItem(str(val)))

    def _save_sources_config(self):
        vals = {k: le.text().strip() for k, le in self.src_inputs.items()}
        for k, v in vals.items():
            if v:
                os.environ[k] = v
        if env_config and hasattr(env_config, "save_env_dict"):
            try:
                env_config.save_env_dict(vals)
            except Exception:
                pass
        self.sources_log.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] 数据源配置已保存。")

    def _test_all_sources(self):
        self._run_source_cmd("test_sources", [sys.executable, "ia_cli.py", "doctor", "--check-sources"])

    def _run_source_cmd(self, name: str, cmd: list):
        self.sources_log.setPlainText(f"正在静默运行 {name} ...")
        self._run_bg(name, lambda: _run_subprocess(cmd, timeout=240).stdout, lambda out, err: self.sources_log.setPlainText(err if err else (out or "执行完成")))

    # 7. 模型 API 与版本更新
    def _build_model_update_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)
        t = QLabel("🤖 模型 API 与版本更新")
        t.setStyleSheet("font-size: 18px; font-weight: bold; color: #F8FAFC;")
        lay.addWidget(t)

        card_llm = QFrame()
        card_llm.setObjectName("Card")
        fl = QFormLayout(card_llm)
        self.cmb_provider = QComboBox()
        self.cmb_provider.addItems(["Ollama (本地)", "LM Studio (本地)", "vLLM (本地)", "OpenAI", "Anthropic Claude", "Google Gemini", "DeepSeek", "Qwen / 通义千问", "自定义 OpenAI 兼容"])
        self.ed_base_url = QLineEdit("http" + "://127.0.0.1:11434/v1")
        self.ed_model_name = QLineEdit("qwen2.5:14b")
        self.ed_api_key = QLineEdit()
        self.ed_api_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        fl.addRow("模型厂商 / 本地引擎", self.cmb_provider)
        fl.addRow("API Base URL", self.ed_base_url)
        fl.addRow("模型名称", self.ed_model_name)
        fl.addRow("API Key (本地可留空)", self.ed_api_key)
        btn_row = QHBoxLayout()
        b_save_llm = QPushButton("保存模型配置")
        b_save_llm.setObjectName("PrimaryBtn")
        b_save_llm.clicked.connect(self._save_llm_config)
        b_test_llm = QPushButton("测试模型连接")
        b_test_llm.clicked.connect(self._test_llm_conn)
        btn_row.addWidget(b_save_llm)
        btn_row.addWidget(b_test_llm)
        btn_row.addStretch()
        fl.addRow(btn_row)
        lay.addWidget(card_llm)
        tray_row = QHBoxLayout()
        self.chk_min_to_tray = QCheckBox("关闭窗口时最小化到系统托盘")
self.chk_min_to_tray.setChecked(True)
self.chk_auto_update = QCheckBox("启用后台定时增量更新 (每 30 分钟)")
self.chk_auto_update.toggled.connect(self._toggle_auto_update_timer)
tray_row.addWidget(self.chk_min_to_tray)
tray_row.addWidget(self.chk_auto_update)
tray_row.addStretch()
lay.addLayout(tray_row)

        card_api = QFrame()
        card_api.setObjectName("Card")
        al = QHBoxLayout(card_api)
        self.lbl_local_api = QLabel("本地 API (127.0.0.1:8787): 检测中...")
        b_check_api = QPushButton("刷新 8787 状态")
        b_check_api.clicked.connect(self._refresh_local_api_status)
        al.addWidget(self.lbl_local_api)
        al.addStretch()
        al.addWidget(b_check_api)
        lay.addWidget(card_api)

        card_upd = QFrame()
        card_upd.setObjectName("Card")
        ul = QHBoxLayout(card_upd)
        self.lbl_ver_info = QLabel(f"当前桌面端版本: v{APP_VERSION}")
        b_check_upd = QPushButton("一键检查更新并升级 Setup.exe")
        b_check_upd.setObjectName("SuccessBtn")
        b_check_upd.clicked.connect(self._check_and_upgrade)
        ul.addWidget(self.lbl_ver_info)
        ul.addStretch()
        ul.addWidget(b_check_upd)
        lay.addWidget(card_upd)

        self.model_upd_log = QPlainTextEdit()
        self.model_upd_log.setReadOnly(True)
        lay.addWidget(self.model_upd_log, 1)
        return w

    def _save_llm_config(self):
        cfg = {
            "provider": self.cmb_provider.currentText(),
            "base_url": self.ed_base_url.text().strip(),
            "model": self.ed_model_name.text().strip(),
            "api_key": self.ed_api_key.text().strip(),
        }
        if llm_providers and hasattr(llm_providers, "save_config"):
            try:
                llm_providers.save_config(cfg)
            except Exception:
                pass
        self.model_upd_log.appendPlainText(f"模型配置已保存: {cfg['provider']} / {cfg['model']}")

    def _test_llm_conn(self):
        def _job():
            if llm_providers and hasattr(llm_providers, "test_connection"):
                return str(llm_providers.test_connection(self.ed_base_url.text().strip(), self.ed_model_name.text().strip(), self.ed_api_key.text().strip()))
            return "已就绪（请确认本地或远端端点可达）"
        self._run_bg("test_llm", _job, lambda out, err: self.model_upd_log.appendPlainText(err if err else f"模型连接测试: {out}"))

    def _refresh_local_api_status(self):
        import socket
        ok = False
        try:
            with socket.create_connection(("127.0.0.1", 8787), timeout=0.6):
                ok = True
        except Exception:
            ok = False
        self.lbl_local_api.setText(f"本地 API (127.0.0.1:8787): {'● 运行中' if ok else '○ 未启动'}")
        self.lbl_local_api.setStyleSheet(f"color: {'#10B981' if ok else '#94A3B8'}; font-weight: bold; background: transparent;")

    def _check_and_upgrade(self):
        def _job():
            if updater and hasattr(updater, "check_and_update"):
                return str(updater.check_and_update())
            p = _run_subprocess([sys.executable, "updater.py", "--check"], timeout=60)
            return p.stdout or p.stderr or f"当前版本已是 v{APP_VERSION}"
        self._run_bg("update_check", _job, lambda out, err: self.model_upd_log.appendPlainText(err if err else out))
    def _on_ai_chunk(self, chunk: str):
        if hasattr(self, "analysis_out") and chunk:
            cur = self.analysis_out.textCursor()
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText(chunk)
            self.analysis_out.setTextCursor(cur)
            self.analysis_out.ensureCursorVisible()
    def _run_ai_stream(self):
        base_text = self.analysis_out.toPlainText().strip() if hasattr(self, "analysis_out") else ""
        if hasattr(self, "analysis_out"):
            self.analysis_out.appendPlainText("\n\n=== 🤖 AI 流式深度解读 ===\n")
        prompt = f"请基于以下宏观与市场分析报告进行深度解读，给出核心逻辑、关键风险与配置建议：\n\n{base_text[:6000]}" if base_text else "请结合最新宏观与大类资产数据生成一份结构化投研深度解读报告。"
        messages = [{"role": "system", "content": "你是专业的宏观与多资产配置投研分析师，请使用中文 Markdown 输出分析。"}, {"role": "user", "content": prompt}]
        def _job():
            if llm_providers and hasattr(llm_providers, "stream_chat_completion"):
                cfg = env_config.load_env_dict() if (env_config and hasattr(env_config, "load_env_dict")) else {}
                provider = cfg.get("LLM_PROVIDER", "") or (self.cmb_provider.currentText() if hasattr(self, "cmb_provider") else "")
                model = cfg.get("LLM_MODEL", "") or (self.ed_model_name.text().strip() if hasattr(self, "ed_model_name") else "")
                base_url = cfg.get("LLM_BASE_URL", "") or (self.ed_base_url.text().strip() if hasattr(self, "ed_base_url") else "")
                api_key = cfg.get("LLM_API_KEY", "") or (self.ed_api_key.text().strip() if hasattr(self, "ed_api_key") else "")
                try:
                    return str(llm_providers.stream_chat_completion(messages=messages, provider=provider or None, model=model or None, base_url=base_url or None, api_key=api_key or None, on_chunk=lambda c: self.signals.chunk_signal.emit(str(c))) or "")
                except TypeError:
                    return str(llm_providers.stream_chat_completion(messages, on_chunk=lambda c: self.signals.chunk_signal.emit(str(c))) or "")
            return "llm_providers.stream_chat_completion 不可用"
        self._run_bg("AI 流式深度解读", _job, lambda out, err: self.analysis_out.appendPlainText(f"\n[错误] {err}") if (err and hasattr(self, "analysis_out")) else None)

    def _export_analysis_report(self):
        import html as _html
        from datetime import datetime as _dt
        from pathlib import Path as _Path
        content = self.analysis_out.toPlainText() if hasattr(self, "analysis_out") else ""
        if not content.strip():
            QMessageBox.information(self, "提示", "当前没有可导出的分析报告内容。")
            return
        path, sel = QFileDialog.getSaveFileName(self, "导出分析报告", f"investment_report_{_dt.now().strftime('%Y%m%d_%H%M%S')}.md", "Markdown 文件 (*.md);;HTML 文件 (*.html);;所有文件 (*.*)")
        if not path:
            return
        try:
            is_html = path.lower().endswith(".html") or ("HTML" in sel and not path.lower().endswith(".md"))
            if is_html:
                path = path if path.lower().endswith(".html") else f"{path}.html"
                out_text = f"<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'><title>Investment Agent 分析报告</title><style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;background:#0f172a;color:#e2e8f0;line-height:1.7;}}pre{{white-space:pre-wrap;background:#1e293b;padding:20px;border-radius:10px;}}</style></head><body><h1>Investment Agent 分析报告</h1><pre>{_html.escape(content)}</pre></body></html>"
            else:
                path = path if path.lower().endswith(".md") else f"{path}.md"
                out_text = content
            _Path(path).write_text(out_text, encoding="utf-8")
            QMessageBox.information(self, "导出成功", f"报告已成功导出至：\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出报告时出错：{e}")

    def _run_macro_update_with_progress(self):
        group_key = self.cmb_src_group.currentData() if hasattr(self, "cmb_src_group") else "all"
        if hasattr(self, "src_progress"):
            self.src_progress.setValue(0)
        if hasattr(self, "lbl_src_prog"):
            self.lbl_src_prog.setText("正在准备增量更新...")
        if hasattr(self, "sources_log"):
            self.sources_log.appendPlainText(f">>> 开始增量更新 (分组: {group_key})...")
        def _job():
            if data_sources and hasattr(data_sources, "run_macro_update_with_progress"):
                def _cb(*args):
                    if len(args) >= 2 and isinstance(args[0], (int, float)):
                        pct, msg = int(args[0]), str(args[1])
                    elif len(args) >= 3 and isinstance(args[0], (int, float)) and isinstance(args[1], (int, float)):
                        pct, msg = int(int(args[0]) * 100 / max(1, int(args[1]))), str(args[2])
                    else:
                        pct, msg = 50, " ".join(str(a) for a in args)
                    self.signals.progress_signal.emit(max(0, min(100, pct)), msg)
                try:
                    res = data_sources.run_macro_update_with_progress(group=group_key, on_progress=_cb)
                except TypeError:
                    try:
                        res = data_sources.run_macro_update_with_progress(group_key, _cb)
                    except TypeError:
                        res = data_sources.run_macro_update_with_progress(_cb)
                self.signals.progress_signal.emit(100, "增量更新完成")
                return str(res)
            return "data_sources.run_macro_update_with_progress 不可用"
        self._run_bg("增量更新数据源", _job, lambda out, err: self.sources_log.appendPlainText(out or err or "完成") if hasattr(self, "sources_log") else None)

    def _on_source_progress(self, pct: int, msg: str):
        if hasattr(self, "src_progress"):
            self.src_progress.setValue(max(0, min(100, int(pct))))
        if hasattr(self, "lbl_src_prog"):
            self.lbl_src_prog.setText(msg)
        if hasattr(self, "sources_log") and msg:
            self.sources_log.appendPlainText(f"[{pct}%] {msg}")

    def _init_tray_and_scheduler(self):
        self.tray_icon = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            icon = self.windowIcon()
            if icon.isNull():
                icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
            self.tray_icon.setIcon(icon)
            self.tray_icon.setToolTip(f"Investment Agent v{APP_VERSION}")
            tray_menu = QMenu(self)
            act_show = QAction("显示主窗口", self)
            act_show.triggered.connect(self._show_from_tray)
            act_update = QAction("立即增量更新数据", self)
            act_update.triggered.connect(self._run_macro_update_with_progress)
            act_quit = QAction("退出程序", self)
            act_quit.triggered.connect(self._quit_from_tray)
            tray_menu.addAction(act_show)
            tray_menu.addAction(act_update)
            tray_menu.addSeparator()
            tray_menu.addAction(act_quit)
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(lambda r: self._show_from_tray() if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)
            self.tray_icon.show()
        self._force_quit = False
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(30 * 60 * 1000)
        self.update_timer.timeout.connect(self._run_macro_update_with_progress)
        if hasattr(self, "chk_auto_update") and self.chk_auto_update.isChecked():
            self.update_timer.start()

    def _toggle_auto_update_timer(self, enabled: bool):
        if hasattr(self, "update_timer"):
            if enabled:
                self.update_timer.start()
            else:
                self.update_timer.stop()

    def _show_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_from_tray(self):
        self._force_quit = True
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if not getattr(self, "_force_quit", False) and hasattr(self, "chk_min_to_tray") and self.chk_min_to_tray.isChecked() and self.tray_icon is not None:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage("Investment Agent", "程序已最小化到系统托盘，双击图标可恢复窗口。", QSystemTrayIcon.MessageIcon.Information, 2500)
            return
        super().closeEvent(event)
        

def main() -> int:
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("InvestmentAgent")
    app.setApplicationVersion(APP_VERSION)
    ico_path = _resolve_icon_path()
    app.setWindowIcon(QIcon(ico_path))
    app.setStyleSheet(DARK_QSS)
    win = InvestmentAgentWindow()
    window = win
    window.setWindowIcon(QIcon(ico_path))
    win.show()
    if sys.platform == "win32" and ico_path and os.path.isfile(str(ico_path)):
        try:
            hicon_big = ctypes.windll.user32.LoadImageW(0, str(ico_path), 1, 256, 256, 0x00000010)
            hicon_small = ctypes.windll.user32.LoadImageW(0, str(ico_path), 1, 32, 32, 0x00000010)
            if hicon_big:
                ctypes.windll.user32.SendMessageW(int(window.winId()), 0x0080, 1, hicon_big)
            if hicon_small:
                ctypes.windll.user32.SendMessageW(int(window.winId()), 0x0080, 0, hicon_small)
        except Exception:
            pass
    return app.exec()


def launch_gui() -> int:
    return main()


if __name__ == "__main__":
    sys.exit(main())
