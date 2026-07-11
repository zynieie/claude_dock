# -*- coding: utf-8 -*-
"""
Claude Dock · V2.9 · 系统托盘入口
================================
- `--scan`     CLI 模式：打印 session JSON 退出（保留兼容 + 单测）
- 默认/无参    GUI 模式：托盘驻留 ◐ + 主坞窗口（点击 ✕ 隐藏到托盘，托盘菜单"退出"才真退出）

打包后 EXE 路径：`ClaudeDock.exe`（PyInstaller onedir 产物）
"""
import sys
import os
import json
import winreg

# CLI 模式：--scan 直接转发到 scanner_core，不启动 Qt
if '--scan' in sys.argv:
    import scanner_core
    sys.stdout.write(json.dumps(scanner_core.scan_sessions(), ensure_ascii=False))
    sys.exit(0)

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QObject

from dock_tray import Dock, HERE, ASSETS

APP_NAME = 'ClaudeDock'
AUTOSTART_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'


# ---------------- 开机自启（HKCU Run 注册表，无 admin 权限）----------------
def _autostart_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(__file__)


def is_autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0,
                            winreg.KEY_READ) as key:
            v, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(v)
    except (OSError, FileNotFoundError):
        return False


def set_autostart(enabled: bool):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = f'"{_autostart_path()}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


# ---------------- 加载图标（frozen 用 _MEIPASS，开发用同级） ----------------
def _load_icon():
    for cand in (os.path.join(ASSETS, 'dock.ico'),
                 os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dock.ico')):
        if os.path.isfile(cand):
            ic = QIcon(cand)
            if not ic.isNull():
                return ic
    # 兜底：Qt 内置 Computer pixmap（通过 QStyle 类访问 enum，实例属性访问不到）
    try:
        from PySide6.QtWidgets import QStyle
        return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    except Exception:
        return QIcon()    # 空图标也强于抛异常


# ---------------- 托盘控制器 ----------------
class TrayController(QObject):
    def __init__(self, app: QApplication, dock: Dock):
        super().__init__()
        self.app = app
        self.dock = dock

        self.tray = QSystemTrayIcon(_load_icon(), parent=app)
        self.tray.setToolTip('◐ Claude 坞 · V2.9')

        menu = QMenu()
        # 当前窗口数（动态更新）
        self.act_status = QAction('● 当前 0 个 Claude 窗口')
        self.act_status.setEnabled(False)
        menu.addAction(self.act_status)
        menu.addSeparator()

        self.act_show = QAction('显示坞')
        self.act_show.triggered.connect(self._show_dock)
        menu.addAction(self.act_show)
        self.act_hide = QAction('隐藏坞')
        self.act_hide.triggered.connect(self.dock.hide)
        menu.addAction(self.act_hide)
        self._sync_show_hide()
        menu.addSeparator()

        # 卡片大小子菜单
        sub_size = menu.addMenu('卡片大小')
        self._size_actions = {}
        for name, val in (('小', 0.85), ('标准', 1.0), ('大', 1.2), ('特大', 1.45)):
            act = sub_size.addAction(name)
            act.setCheckable(True)
            act.setChecked(abs(val - float(self.dock.cfg['scale'])) < 0.01)
            act.triggered.connect(lambda _=False, v=val: self._apply_size(v))
            self._size_actions[act] = val
        menu.addSeparator()

        # 开机启动
        self.act_autostart = QAction('☐ 开机时启动')
        self.act_autostart.setCheckable(True)
        self.act_autostart.setChecked(is_autostart_enabled())
        self.act_autostart.toggled.connect(self._toggle_autostart)
        menu.addAction(self.act_autostart)
        menu.addSeparator()

        menu.addAction('关于 Claude Dock').triggered.connect(self._about)
        menu.addAction('退出').triggered.connect(self._quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        # 主坞计数变化时刷新菜单（QLabel 没有 textChanged 信号 → 包一层 setText）
        _orig_setText = self.dock.count.setText
        def _wrapped_setText(t, _orig=_orig_setText):
            _orig(t)
            self._sync_status(t)
        self.dock.count.setText = _wrapped_setText
        # 主坞显隐变化时同步菜单（用 installEventFilter 太重，直接监听 hide/show 即可）
        self.dock.installEventFilter(self)

    def eventFilter(self, obj, ev):
        # dock 隐藏/显示时同步菜单
        if obj is self.dock and ev.type() in (ev.Type.Hide, ev.Type.Show):
            self._sync_show_hide()
        return False

    # ---- 显隐同步 ----
    def _sync_show_hide(self):
        visible = self.dock.isVisible()
        self.act_show.setEnabled(not visible)
        self.act_hide.setEnabled(visible)

    def _sync_status(self, _txt):
        self.act_status.setText(f'● 当前 {self.dock._count} 个 Claude 窗口')

    def _show_dock(self):
        self.dock.show()
        self.dock.raise_()
        self.dock.activateWindow()
        self._sync_show_hide()

    # ---- 双击切显隐 ----
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:        # 单/双击都属 Trigger
            if self.dock.isVisible():
                self.dock.hide()
            else:
                self._show_dock()

    # ---- 卡片大小 ----
    def _apply_size(self, val: float):
        self.dock.cfg['scale'] = val
        self.dock._apply()
        for act, v in self._size_actions.items():
            act.setChecked(abs(v - val) < 0.01)

    # ---- 开机启动 ----
    def _toggle_autostart(self, on: bool):
        if not set_autostart(on):
            QMessageBox.warning(self.dock, 'Claude Dock',
                                '无法写入注册表，请检查权限')
            self.act_autostart.blockSignals(True)
            self.act_autostart.setChecked(not on)
            self.act_autostart.blockSignals(False)

    # ---- 关于 / 退出 ----
    def _about(self):
        QMessageBox.about(
            self.dock, '关于 Claude Dock',
            '<h3>◐ Claude Dock · V2.9</h3>'
            '<p>Claude Code 悬浮收纳坞 · Web 3D 版</p>'
            '<hr>'
            '<p>• 系统托盘常驻</p>'
            '<p>• 卡片 1.5s 实时刷新</p>'
            '<p>• 卡片可拖出坞跟手</p>'
            '<p>• 滚轮切换窗口</p>'
            '<p>• 右键托盘 / 主坞 设置</p>'
        )

    def _quit(self):
        try:
            self.dock._save_cfg()
        except Exception:
            pass
        self.app.quit()


# ---------------- main ----------------
def main():
    # 高 DPI 全栈开启（修复 QtWebEngine 文字发虚）
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except AttributeError:
        pass
    # AA_UseHighDpiPixmaps 在 PySide6 6.6+ 已废弃，默认就是高 DPI 图，无需手动开
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)        # 托盘模式下关窗不退出
    app.setApplicationName('Claude Dock')

    dock = Dock()
    dock.show()                                 # 首次启动显坞
    tray = TrayController(app, dock)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()