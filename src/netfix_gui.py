# -*- coding: utf-8 -*-
"""
NetFix 网络异常修复工具 — GUI 主程序（PySide6）
页面：P-01 一键体检 / P-02 修复确认 / P-03 结果与回滚

配色规范：全局 QSS + 对象名，正文对比度全部 ≥ 4.5:1
"""
import os
import sys

def res_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QTextEdit, QScrollArea, QFrame, QMessageBox,
    QProgressBar, QFileDialog, QSizePolicy
)

import netfix_core as core

# ---------- 高对比协调色板（文字对比度 ≥ 4.5:1） ----------
C_PRIMARY   = "#2E5C8A"   # 沉稳蓝：主按钮，白字对比 6.4:1
C_ACCENT    = "#0B6E5F"   # 深青绿：正常态，白底对比 5.6:1
C_WARN      = "#9A5B09"   # 深琥珀：注意态，白底对比 5.1:1
C_ERR       = "#B3261E"   # 暗红：异常态，白底对比 5.6:1
C_BG        = "#F4F7FB"   # 页面底色
C_CARD      = "#FFFFFF"   # 卡片底
C_TEXT      = "#1A2433"   # 正文：白底对比 ≈14:1
C_SUB       = "#566274"   # 次要文字：白底对比 ≈5.8:1
C_BORDER    = "#DCE3EC"   # 边框
C_WARN_BG   = "#FFF8E8"
C_WARN_BD   = "#EDD6A6"
C_OK_BG     = "#E9F5F1"
C_OK_BD     = "#BFE3D7"
C_ERR_BG    = "#FCEDEC"
C_ERR_BD    = "#F0C4C0"

LEVEL_STYLE = {
    "ok":   (C_ACCENT, "正常", "●", C_OK_BG, C_OK_BD),
    "warn": (C_WARN,   "注意", "●", C_WARN_BG, C_WARN_BD),
    "err":  (C_ERR,    "异常", "●", C_ERR_BG, C_ERR_BD),
}

# ---------- 全局 QSS：统一色板，所有规则用完整选择器 ----------
GLOBAL_QSS = f"""
QWidget {{
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {C_TEXT};
}}
QMainWindow, QDialog {{ background: {C_BG}; }}
QStatusBar {{ color: {C_SUB}; background: {C_BG}; border-top: 1px solid {C_BORDER}; }}

QLabel {{ color: {C_TEXT}; background: transparent; }}

QPushButton {{
    background: {C_CARD};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 6px 16px;
    min-height: 34px;
}}
QPushButton:hover {{ background: #EDF2F8; border-color: #B9C9DC; }}
QPushButton:pressed {{ background: #E2EAF4; }}
QPushButton:disabled {{ color: #A8B2BF; background: #F7F9FC; border-color: {C_BORDER}; }}
QPushButton#primary {{
    background: {C_PRIMARY}; color: #FFFFFF; border: 1px solid {C_PRIMARY}; font-weight: 600;
}}
QPushButton#primary:hover {{ background: #254C74; border-color: #254C74; }}
QPushButton#primary:disabled {{ background: #AFC0D2; color: #FFFFFF; border-color: #AFC0D2; }}
QPushButton#danger {{ background: {C_CARD}; color: {C_ERR}; border: 1px solid {C_ERR}; }}
QPushButton#danger:hover {{ background: {C_ERR_BG}; }}
QPushButton#danger:disabled {{ color: #C9C9C9; border-color: {C_BORDER}; background: {C_CARD}; }}
QPushButton#tiny {{ min-height: 24px; padding: 2px 10px; font-size: 12px; }}
QPushButton#link {{
    background: transparent; border: none; color: {C_PRIMARY};
    text-decoration: underline; min-height: 24px;
}}

QFrame#card {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px; }}
QFrame#hintWarn {{ background: {C_WARN_BG}; border: 1px solid {C_WARN_BD}; border-radius: 6px; }}
QFrame#hintOk {{ background: {C_OK_BG}; border: 1px solid {C_OK_BD}; border-radius: 6px; }}
QFrame#row {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 6px; }}
QFrame#accentBar {{ background: {C_PRIMARY}; border: none; border-radius: 3px; }}

QScrollArea {{ border: 1px solid {C_BORDER}; border-radius: 8px; background: {C_CARD}; }}
QScrollArea > QWidget > QWidget {{ background: {C_CARD}; }}
QTextEdit {{
    background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 6px;
    color: {C_TEXT}; padding: 8px; selection-background-color: #C7D9EC;
}}
QProgressBar {{
    border: 1px solid {C_BORDER}; border-radius: 7px; height: 15px;
    background: {C_CARD}; text-align: center; color: {C_TEXT};
}}
QProgressBar::chunk {{ background: {C_PRIMARY}; border-radius: 7px; }}
QCheckBox {{ color: {C_TEXT}; spacing: 6px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid #9FB0C4; border-radius: 3px; background: {C_CARD}; }}
QCheckBox::indicator:checked {{ background: {C_PRIMARY}; border: 1px solid {C_PRIMARY}; }}
QMessageBox {{ background: {C_CARD}; }}
QMessageBox QLabel {{ color: {C_TEXT}; }}
QToolTip {{ background: {C_TEXT}; color: #FFFFFF; border: none; padding: 4px 6px; }}
"""


class ScanWorker(QThread):
    done = Signal(list)
    def run(self):
        self.done.emit(core.run_scan())


class FixWorker(QThread):
    progress = Signal(str)
    done = Signal(list)
    def __init__(self, keys):
        super().__init__()
        self.keys = keys
    def run(self):
        log = []
        for key in self.keys:
            label = next((r["label"] for r in core.REPAIRS if r["key"] == key), key)
            self.progress.emit(f"正在执行：{label} ...")
            ok, msg = core.apply_repair(key)
            log.append(f"[{'成功' if ok else '失败'}] {label}：{msg}")
        self.done.emit(log)


class TestWorker(QThread):
    done = Signal(tuple)
    def run(self):
        self.done.emit(core.self_test())


class NetFixApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetFix 网络异常修复工具")
        self.setMinimumSize(940, 640)
        self.resize(1040, 720)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.scan_results = []
        self.repair_log = []
        self.backup_dir = None
        self.checkboxes = {}

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.page_scan = self.build_scan_page()
        self.page_fix = self.build_fix_page()
        self.page_result = self.build_result_page()
        for p in (self.page_scan, self.page_fix, self.page_result):
            self.stack.addWidget(p)

        self.statusBar().showMessage("就绪 · 本工具完全离线，体检为只读操作")

    # ---------- 通用组件 ----------
    def title_block(self, title, subtitle):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(12)
        bar = QFrame()
        bar.setObjectName("accentBar")
        bar.setFixedSize(5, 42)
        h.addWidget(bar)
        v = QVBoxLayout()
        v.setSpacing(3)
        t = QLabel(title)
        t.setStyleSheet(f"font-size:19px;font-weight:600;color:{C_TEXT};")
        s = QLabel(subtitle)
        s.setStyleSheet(f"font-size:12px;color:{C_SUB};")
        v.addWidget(t)
        v.addWidget(s)
        h.addLayout(v, 1)
        return w

    def btn(self, text, kind="ghost", minw=120, tiny=False):
        b = QPushButton(text)
        b.setMinimumWidth(minw)
        if tiny:
            b.setObjectName("tiny")
        elif kind == "primary":
            b.setObjectName("primary")
        elif kind == "danger":
            b.setObjectName("danger")
        b.setCursor(Qt.PointingHandCursor)
        return b

    # ---------- P-01 体检页 ----------
    def build_scan_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)

        root.addWidget(self.title_block(
            "网络健康体检",
            "只读扫描 8 条网络通道，定位故障所在 · 不会修改任何设置"))

        admin_hint = QLabel()
        if not core.is_admin():
            admin_hint.setText("⚠ 当前非管理员权限：体检可用，但 Winsock/TCP-IP 重置等修复项需要提权")
            admin_hint.setStyleSheet(
                f"color:{C_WARN};background:{C_WARN_BG};border:1px solid {C_WARN_BD};"
                f"border-radius:6px;padding:9px 12px;font-size:12px;"
            )
        else:
            admin_hint.setText("✓ 已具备管理员权限，全部修复项可用")
            admin_hint.setStyleSheet(
                f"color:{C_ACCENT};background:{C_OK_BG};border:1px solid {C_OK_BD};"
                f"border-radius:6px;padding:9px 12px;font-size:12px;"
            )
        admin_hint.setWordWrap(True)
        root.addWidget(admin_hint)

        btnrow = QHBoxLayout()
        btnrow.setSpacing(12)
        self.scan_btn = self.btn("一键体检", "primary", 130)
        self.scan_btn.clicked.connect(self.do_scan)
        self.help_btn = self.btn("为什么浏览器断网，其他软件却正常？", minw=210)
        self.help_btn.clicked.connect(self.show_knowledge)
        self.elevate_btn = self.btn("以管理员身份重启")
        self.elevate_btn.clicked.connect(self.elevate)
        self.elevate_btn.setVisible(not core.is_admin())
        btnrow.addWidget(self.scan_btn)
        btnrow.addWidget(self.help_btn)
        btnrow.addWidget(self.elevate_btn)
        btnrow.addStretch(1)
        root.addLayout(btnrow)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        # 结果列表
        self.scan_container = QWidget()
        self.scan_layout = QVBoxLayout(self.scan_container)
        self.scan_layout.setContentsMargins(10, 10, 10, 10)
        self.scan_layout.setSpacing(8)
        self.scan_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.scan_container)
        root.addWidget(scroll, 1)

        footer = QHBoxLayout()
        self.scan_summary = QLabel("尚未体检 · 点击「一键体检」开始")
        self.scan_summary.setStyleSheet(f"color:{C_SUB};font-size:12px;")
        self.to_fix_btn = self.btn("下一步：选择修复 →", "primary", 160)
        self.to_fix_btn.setEnabled(False)
        self.to_fix_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_fix))
        footer.addWidget(self.scan_summary)
        footer.addStretch(1)
        footer.addWidget(self.to_fix_btn)
        root.addLayout(footer)
        return page

    def render_scan_results(self, results):
        while self.scan_layout.count():
            item = self.scan_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        counts = {"ok": 0, "warn": 0, "err": 0}
        for it in results:
            counts[it["level"]] += 1
            color, label, dot, bg, bd = LEVEL_STYLE[it["level"]]
            row = QFrame()
            row.setObjectName("row")
            h = QHBoxLayout(row)
            h.setContentsMargins(12, 9, 12, 9)
            h.setSpacing(10)
            dotlbl = QLabel(dot)
            dotlbl.setStyleSheet(f"color:{color};font-size:15px;")
            h.addWidget(dotlbl)
            name = QLabel(it["name"])
            name.setMinimumWidth(140)
            name.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;")
            h.addWidget(name)
            summ = QLabel(it["summary"])
            summ.setStyleSheet(f"color:{color};font-size:12px;font-weight:600;")
            summ.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            h.addWidget(summ, 1)
            badge = QLabel(label)
            badge.setStyleSheet(
                f"color:#FFFFFF;background:{color};border-radius:9px;"
                f"padding:2px 10px;font-size:11px;font-weight:600;"
            )
            h.addWidget(badge)
            detail_btn = self.btn("依据", tiny=True, minw=52)
            detail_btn.clicked.connect(
                lambda _, d=it["detail"], n=it["name"]: self.show_detail(n, d)
            )
            h.addWidget(detail_btn)
            self.scan_layout.addWidget(row)
        self.scan_layout.addStretch(1)
        self.scan_summary.setText(
            f"体检完成：正常 {counts['ok']} · 注意 {counts['warn']} · 异常 {counts['err']}"
        )

    def do_scan(self):
        self.scan_btn.setEnabled(False)
        self.to_fix_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.statusBar().showMessage("正在只读体检 ...")
        self.worker = ScanWorker()
        self.worker.done.connect(self.on_scan_done)
        self.worker.start()

    def on_scan_done(self, results):
        self.scan_results = results
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.render_scan_results(results)
        self.scan_btn.setEnabled(True)
        self.to_fix_btn.setEnabled(True)
        n_err = sum(1 for r in results if r["level"] == "err")
        self.statusBar().showMessage(
            f"体检完成：发现 {n_err} 项异常，可进入修复" if n_err else "体检完成：未发现致命异常"
        )

    def show_detail(self, name, detail):
        box = QMessageBox(self)
        box.setWindowTitle(f"检查依据 — {name}")
        box.setText(detail)
        box.exec()

    def show_knowledge(self):
        text = (
            "为什么浏览器打不开网页，但微信/QQ/下载器却能用？\n\n"
            "Windows 有 4 套互相独立的上网通道：\n"
            "① WinINET 系统代理 —— Edge/浏览器读取这里\n"
            "② WinHTTP —— 系统更新、部分服务使用\n"
            "③ 环境变量代理 —— git/npm/python/curl 读取\n"
            "④ 软件自带 socket —— 微信/QQ/Steam 等直连\n\n"
            "故障只落在某一条通道时，就出现「这家断网、那家正常」。\n"
            "你这次的问题：系统代理开关被打开、指向 127.0.0.1:7897，\n"
            "但该端口没有程序监听。浏览器把每个请求都交给这个「死代理」，\n"
            "所以打不开；其他软件走②④，直连外网，所以正常。\n\n"
            "这类问题通常是代理/加速器软件退出或卸载后，\n"
            "系统代理开关没还原造成的配置残留。"
        )
        box = QMessageBox(self)
        box.setWindowTitle("多因素知识说明")
        box.setText(text)
        box.exec()

    def elevate(self):
        try:
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            self.close()
        except Exception as e:
            QMessageBox.warning(self, "提权失败", str(e))

    # ---------- P-02 修复页 ----------
    def build_fix_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)
        root.addWidget(self.title_block("确认修复", "修复前将自动创建配置快照，任何改动都可回滚"))

        backup_box = QFrame()
        backup_box.setObjectName("card")
        bv = QVBoxLayout(backup_box)
        bv.setContentsMargins(14, 12, 14, 12)
        bv.setSpacing(4)
        bvl = QLabel("快照保存位置（修复前自动生成）：")
        bvl.setStyleSheet(f"color:{C_SUB};font-size:12px;")
        self.backup_path_label = QLabel("（将在点击「确认修复」时生成）")
        self.backup_path_label.setStyleSheet(
            f"color:{C_TEXT};font-size:12px;font-family:Consolas,monospace;"
        )
        self.backup_path_label.setWordWrap(True)
        bv.addWidget(bvl)
        bv.addWidget(self.backup_path_label)
        root.addWidget(backup_box)

        warn = QLabel(
            "说明：本工具只处理系统级代理与网络配置残留，不会清空 Wi-Fi 密码、不改防火墙、不动 hosts 自定义条目。"
        )
        warn.setStyleSheet(
            f"color:{C_WARN};font-size:12px;background:{C_WARN_BG};"
            f"border:1px solid {C_WARN_BD};border-radius:6px;padding:9px 12px;"
        )
        warn.setWordWrap(True)
        root.addWidget(warn)

        check_label = QLabel("选择要修复的项目（默认只勾选推荐项）：")
        check_label.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;")
        root.addWidget(check_label)

        self.check_container = QWidget()
        self.check_layout = QVBoxLayout(self.check_container)
        self.check_layout.setContentsMargins(8, 8, 8, 8)
        self.check_layout.setSpacing(6)
        for r in core.REPAIRS:
            cb = QCheckBox()
            title = QLabel(r["label"])
            title.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;")
            desc = QLabel(r["desc"] + ("  · 需管理员/重启" if r["admin"] else ""))
            desc.setStyleSheet(f"color:{C_SUB};font-size:11px;")
            row = QFrame()
            row.setObjectName("row")
            h = QHBoxLayout(row)
            h.setContentsMargins(12, 8, 12, 8)
            v = QVBoxLayout()
            v.setSpacing(1)
            v.addWidget(title)
            v.addWidget(desc)
            cb.setChecked(r["default"])
            h.addWidget(cb)
            h.addLayout(v, 1)
            self.check_layout.addWidget(row)
            self.checkboxes[r["key"]] = cb
        self.check_layout.addStretch(1)
        scroll2 = QScrollArea()
        scroll2.setWidgetResizable(True)
        scroll2.setWidget(self.check_container)
        root.addWidget(scroll2, 1)

        self.fix_log = QTextEdit()
        self.fix_log.setReadOnly(True)
        self.fix_log.setMinimumHeight(88)
        root.addWidget(self.fix_log)

        footer = QHBoxLayout()
        footer.setSpacing(12)
        back = self.btn("← 返回体检")
        back.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_scan))
        self.fix_btn = self.btn("确认修复（先备份）", "primary", 170)
        self.fix_btn.clicked.connect(self.do_fix)
        footer.addWidget(back)
        footer.addStretch(1)
        footer.addWidget(self.fix_btn)
        root.addLayout(footer)
        return page

    def do_fix(self):
        keys = [k for k, cb in self.checkboxes.items() if cb.isChecked()]
        if not keys:
            QMessageBox.information(self, "未选择", "请至少勾选一项修复内容")
            return
        need_admin = any(r["admin"] for r in core.REPAIRS if r["key"] in keys)
        if need_admin and not core.is_admin():
            ret = QMessageBox.question(
                self, "需要管理员权限",
                "你勾选的修复项需要管理员权限。请以管理员身份重启后再修复。\n是否现在提权重启？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.Yes:
                self.elevate()
            return
        ret = QMessageBox.question(
            self, "最终确认",
            f"即将执行 {len(keys)} 项修复，并先创建配置快照。\n确认继续？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        self.fix_btn.setEnabled(False)
        self.backup_dir = core.create_backup()
        self.backup_path_label.setText(self.backup_dir)
        self.fix_log.clear()
        self.fix_log.append(f"已创建快照：{self.backup_dir}")
        self.statusBar().showMessage("正在修复 ...")
        self.fworker = FixWorker(keys)
        self.fworker.progress.connect(lambda s: self.fix_log.append(s))
        self.fworker.done.connect(self.on_fix_done)
        self.fworker.start()

    def on_fix_done(self, log):
        self.repair_log = log
        self.result_log.setText("\n".join(log))
        self.fix_btn.setEnabled(True)
        self.statusBar().showMessage("修复完成，请查看结果")
        self.stack.setCurrentWidget(self.page_result)
        self.do_selftest()

    # ---------- P-03 结果页 ----------
    def build_result_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)
        root.addWidget(self.title_block("修复结果与回滚", "修复后自动进行连通性自检，确认浏览器是否真的恢复"))

        hero = QFrame()
        hero.setObjectName("hintOk")
        hh = QHBoxLayout(hero)
        hh.setContentsMargins(14, 12, 14, 12)
        hh.setSpacing(12)
        icon = QLabel("✓")
        icon.setStyleSheet(f"color:{C_ACCENT};font-size:26px;font-weight:600;")
        hh.addWidget(icon)
        hv = QVBoxLayout()
        hv.setSpacing(2)
        t = QLabel("修复已完成")
        t.setStyleSheet(f"color:{C_TEXT};font-size:15px;font-weight:600;")
        self.result_sub = QLabel("正在自检 ...")
        self.result_sub.setStyleSheet(f"color:{C_SUB};font-size:12px;")
        hv.addWidget(t)
        hv.addWidget(self.result_sub)
        hh.addLayout(hv, 1)
        root.addWidget(hero)

        self.selftest_label = QLabel("连通性自检：等待结果")
        self.selftest_label.setStyleSheet(
            f"color:{C_TEXT};font-size:13px;background:{C_CARD};"
            f"border:1px solid {C_BORDER};border-radius:6px;padding:10px 12px;"
        )
        self.selftest_label.setWordWrap(True)
        root.addWidget(self.selftest_label)

        log_label = QLabel("修复记录：")
        log_label.setStyleSheet(f"color:{C_TEXT};font-size:13px;font-weight:600;")
        root.addWidget(log_label)
        self.result_log = QTextEdit()
        self.result_log.setReadOnly(True)
        root.addWidget(self.result_log, 1)

        reboot = QLabel("提示：Winsock / TCP-IP 重置需重启电脑后完全生效。")
        reboot.setStyleSheet(f"color:{C_WARN};font-size:12px;")
        root.addWidget(reboot)

        footer = QHBoxLayout()
        footer.setSpacing(12)
        self.rollback_btn = self.btn("一键回滚", "danger", 110)
        self.rollback_btn.clicked.connect(self.do_rollback)
        self.export_btn = self.btn("导出报告")
        self.export_btn.clicked.connect(self.do_export)
        again = self.btn("重新体检")
        again.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_scan))
        footer.addWidget(self.rollback_btn)
        footer.addWidget(self.export_btn)
        footer.addStretch(1)
        footer.addWidget(again)
        root.addLayout(footer)
        return page

    def do_selftest(self):
        self.tworker = TestWorker()
        self.tworker.done.connect(self.on_test_done)
        self.tworker.start()

    def on_test_done(self, result):
        dns_ok, dns_msg, http_ok, http_msg = result
        if dns_ok and http_ok:
            self.selftest_label.setText(
                f"✓ 自检通过：DNS {dns_msg} · {http_msg}。浏览器应已恢复正常。"
            )
            self.selftest_label.setStyleSheet(
                f"color:{C_ACCENT};font-size:13px;background:{C_OK_BG};"
                f"border:1px solid {C_OK_BD};border-radius:6px;padding:10px 12px;"
            )
        else:
            self.selftest_label.setText(
                f"⚠ 自检未完全通过：DNS [{dns_msg}] · HTTP [{http_msg}]。\n"
                "建议：重启电脑后再测；若仍失败，请检查网线/Wi-Fi 或联系网络管理员。"
            )
            self.selftest_label.setStyleSheet(
                f"color:{C_WARN};font-size:13px;background:{C_WARN_BG};"
                f"border:1px solid {C_WARN_BD};border-radius:6px;padding:10px 12px;"
            )
        self.result_sub.setText(f"已执行 {len(self.repair_log)} 项修复 · 快照：{self.backup_dir or '无'}")

    def do_rollback(self):
        if not self.backup_dir:
            QMessageBox.information(self, "无快照", "当前没有可回滚的快照")
            return
        ret = QMessageBox.question(
            self, "确认回滚",
            f"将从快照恢复配置：\n{self.backup_dir}\n\n确认继续？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        ok, msg = core.rollback(self.backup_dir)
        if ok:
            QMessageBox.information(self, "回滚完成", "配置已从快照恢复：\n" + msg)
            self.statusBar().showMessage("已回滚到修复前状态")
        else:
            QMessageBox.warning(self, "回滚失败", msg)

    def do_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出诊断报告",
            os.path.join(core.REPORT_DIR, f"netfix-report-{core._ts()}.html"),
            "HTML 文件 (*.html)",
        )
        if not path:
            return
        core.export_report(self.scan_results, self.repair_log, self.backup_dir, path)
        QMessageBox.information(self, "导出成功", f"报告已保存到：\n{path}")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    app.setStyleSheet(GLOBAL_QSS)
    w = NetFixApp()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
