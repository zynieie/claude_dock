# -*- coding: utf-8 -*-
"""
Claude Code 悬浮收纳坞 · Web 3D 版 (web坞V4.0)
=============================================
相对 V2.7:
  - 卡片坞内拖拽重排: 长按拖动, 抬起幽灵卡片 + 蓝色插入线, 松手即时换位
  - 卡片拖出坞: 卡片"消失", Python 16ms 心跳把对应 Claude 窗口实时跟手; 松手停在落点
    拖回坞内则停止跟手, 卡片"复活"留在原位
继承: 顺序固定 / 高DPI / DWM圆角 / 滚轮切换 / 标题跑马灯 / 右键设置 / 字体 / 右键标题开文件夹
"""
import sys
import os
import json
import subprocess
import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
dwmapi = ctypes.WinDLL('dwmapi')

# 打包模式检测 (PyInstaller --onefile 会设置 sys._MEIPASS)
_PACKAGED = getattr(sys, '_MEIPASS', None) is not None

if _PACKAGED:
    HERE = sys._MEIPASS                                    # 打包资源目录 (dashboard.html, scanner)
    EXE_DIR = os.path.dirname(sys.executable)              # .exe 所在目录
    CONFIG = os.path.join(os.path.expanduser('~'), '.claude_dock_web.json')
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = HERE
    CONFIG = os.path.join(HERE, 'dock_web_config.json')

SCANNER = os.path.join(os.path.dirname(HERE), 'python坞V1.08', 'claude_dock.py')
DEFAULT_CFG = {'bg': '#1b1b20', 'fg': '#f2f2f7', 'scale': 1.0, 'font': ''}
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010
MARGIN = 12
HEADER_H = 34
MIN_W, MIN_H = 220, 150


def focus_window(hwnd):
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)
    fg = user32.GetForegroundWindow()
    cur = kernel32.GetCurrentThreadId()
    tgt = user32.GetWindowThreadProcessId(fg, None)
    user32.AttachThreadInput(tgt, cur, True)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(tgt, cur, False)


from PySide6.QtWidgets import (QApplication, QWidget, QFrame, QLabel, QVBoxLayout,
                               QHBoxLayout, QPushButton, QGraphicsDropShadowEffect,
                               QMenu, QColorDialog, QFontDialog)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject, Slot, QUrl
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication


class Bridge(QObject):
    """网页 -> Python 的回调桥。"""
    menuRequested = Signal()
    openFolderRequested = Signal()
    dragStartSig = Signal(int, int, int)
    dragOutsideSig = Signal(int, int, int)
    dragReturnSig = Signal()
    dragEndSig = Signal(bool, int, int)
    dragDropSig = Signal(int, int, int)

    @Slot(str)
    def jump(self, hwnd):
        try:
            focus_window(int(hwnd))
        except Exception:
            pass

    @Slot()
    def menu(self):
        self.menuRequested.emit()

    @Slot()
    def openFolder(self):
        self.openFolderRequested.emit()

    @Slot(int, int, int)
    def dragStart(self, hwnd, x, y):
        self.dragStartSig.emit(int(hwnd), int(x), int(y))

    @Slot(int, int, int)
    def dragOutside(self, hwnd, x, y):
        self.dragOutsideSig.emit(int(hwnd), int(x), int(y))

    @Slot()
    def dragReturn(self):
        self.dragReturnSig.emit()

    @Slot(bool, int, int)
    def dragEnd(self, in_dock, x, y):
        self.dragEndSig.emit(bool(in_dock), int(x), int(y))

    @Slot(int, int, int)
    def dragDrop(self, hwnd, x, y):
        self.dragDropSig.emit(int(hwnd), int(x), int(y))


class ScanWorker(QThread):
    done = Signal(list)

    def run(self):
        try:
            if _PACKAGED:
                # 打包模式: 直接 import 扫描器模块 (省掉 subprocess + 捆绑 Python 解释器)
                from claude_dock_scanner import scan_sessions
                data = scan_sessions()
            else:
                out = subprocess.run([sys.executable, SCANNER, '--scan'],
                                     capture_output=True, timeout=12,
                                     creationflags=CREATE_NO_WINDOW)
                data = json.loads(out.stdout.decode('utf-8', 'replace') or '[]')
        except Exception:
            data = []
        self.done.emit(data)


STYLE = """
#panel { background: #1b1b20; border-radius: 0; }
#header { color:#f2f2f7; font-size:13px; font-weight:600; }
#count  { color:#8e8e93; font-size:12px; }
#tool   { background:transparent; color:#8e8e93; border:none; font-size:15px; }
#tool:hover { color:#f2f2f7; }
#plus   { background:transparent; color:#3ddc84; border:none; font-size:18px; font-weight:700; }
#plus:hover { color:#5cff9d; }
"""

MENU_STYLE = """
QMenu { background:#26262b; color:#f2f2f7; border:1px solid rgba(255,255,255,0.12);
        border-radius:8px; padding:4px; }
QMenu::item { padding:6px 20px; border-radius:6px; font-size:12px; }
QMenu::item:selected { background:#0a84ff; }
QMenu::separator { height:1px; background:rgba(255,255,255,0.1); margin:4px 8px; }
"""


class Dock(QWidget):
    def __init__(self):
        super().__init__()
        self.pinned = True
        self._drag = None
        self._styled = False
        self._n = -1
        self._count = 0
        self.cfg = self._load_cfg()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(MIN_W, MIN_H)
        self.resize(300, 400)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.panel = QFrame()
        self.panel.setObjectName('panel')
        outer.addWidget(self.panel)

        pl = QVBoxLayout(self.panel)
        pl.setContentsMargins(12, 10, 10, 6)
        pl.setSpacing(6)

        header = QHBoxLayout()
        self.htitle = QLabel('◐ Claude 坞 · 3D')
        self.htitle.setObjectName('header')
        self.htitle.setContextMenuPolicy(Qt.CustomContextMenu)
        self.htitle.customContextMenuRequested.connect(lambda _: self.open_folder())
        self.htitle.setToolTip('右键：打开项目文件夹')
        self.count = QLabel('')
        self.count.setObjectName('count')
        self.new_btn = QPushButton('+')
        self.new_btn.setObjectName('plus')
        self.new_btn.setToolTip('新开一个 Claude Code 窗口')
        self.new_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.new_btn.clicked.connect(self.open_new)
        self.pin_btn = QPushButton('📌')
        self.pin_btn.setObjectName('tool')
        self.pin_btn.setToolTip('置顶开/关')
        self.pin_btn.clicked.connect(self.toggle_pin)
        close_btn = QPushButton('✕')
        close_btn.setObjectName('tool')
        close_btn.clicked.connect(self.close)
        header.addWidget(self.htitle)
        header.addSpacing(6)
        header.addWidget(self.count)
        header.addStretch(1)
        header.addWidget(self.new_btn)
        header.addWidget(self.pin_btn)
        header.addWidget(close_btn)
        pl.addLayout(header)

        self.view = QWebEngineView()
        self.view.setContextMenuPolicy(Qt.NoContextMenu)      # 禁网页内核自带右键菜单
        self.view.page().setBackgroundColor(QColor(self.cfg['bg']))
        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.bridge.menuRequested.connect(self.open_settings)
        self.bridge.openFolderRequested.connect(self.open_folder)
        self.bridge.dragStartSig.connect(self._drag_start)
        self.bridge.dragOutsideSig.connect(self._drag_outside)
        self.bridge.dragReturnSig.connect(self._drag_return)
        self.bridge.dragDropSig.connect(self._drag_drop)
        self.bridge.dragEndSig.connect(self._drag_end)
        self.channel.registerObject('bridge', self.bridge)
        self._font = self.cfg.get('font', '')
        self.view.page().setWebChannel(self.channel)
        self.view.load(QUrl.fromLocalFile(os.path.join(HERE, 'dashboard.html')))
        self.view.loadFinished.connect(self._on_loaded)
        pl.addWidget(self.view, 1)

        self.setStyleSheet(STYLE)
        self._apply_best_view()

        self._worker = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)

    # ---- 数据 ----
    def _on_loaded(self, ok):
        self._push_style()
        self.refresh()

    def refresh(self):
        if self._worker and self._worker.isRunning():
            return
        self._worker = ScanWorker()
        self._worker.done.connect(self.apply_sessions)
        self._worker.start()

    def apply_sessions(self, sessions):
        self._count = len(sessions)
        self.count.setText('· %d 个窗口' % self._count)
        self.view.page().runJavaScript(
            "window.setSessions && window.setSessions(%s)" % json.dumps(sessions, ensure_ascii=False))
        if self._count != self._n:
            self._n = self._count
            self._fit(self._n)

    def _fit(self, n):
        s = float(self.cfg['scale'])
        card_h, gap = 60 * s, 10 * s
        content = max(1, n) * card_h + (max(1, n) - 1) * gap + 14 * s
        h = 10 + HEADER_H + content + 6
        try:
            avail = self.screen().availableGeometry().height() - 48
        except Exception:
            avail = 1000
        self.resize(self.width(), max(MIN_H, min(int(h), avail)))

    # ---- 右键设置 ----
    def _push_style(self):
        c = self.cfg
        f = self._font.replace("'", "\\'") if self._font else ''
        self.view.page().runJavaScript(
            "window.setStyle && window.setStyle('%s','%s',%s,'%s')" % (c['bg'], c['fg'], c['scale'], f))
        self.view.page().setBackgroundColor(QColor(c['bg']))

    def open_settings(self):
        m = QMenu(self)
        m.setStyleSheet(MENU_STYLE)
        a_bg = m.addAction('背景颜色…')
        a_fg = m.addAction('字体颜色…')
        a_font = m.addAction('字体…')
        sub = m.addMenu('卡片大小')
        size_acts = {}
        for name, val in (('小', 0.85), ('标准', 1.0), ('大', 1.2), ('特大', 1.45)):
            act = sub.addAction(name)
            act.setCheckable(True)
            act.setChecked(abs(val - float(self.cfg['scale'])) < 0.01)
            size_acts[act] = val
        m.addSeparator()
        a_reset = m.addAction('恢复默认')
        chosen = m.exec(QCursor.pos())
        if chosen is None:
            return
        if chosen is a_bg:
            col = QColorDialog.getColor(QColor(self.cfg['bg']), self, '背景颜色')
            if col.isValid():
                self.cfg['bg'] = col.name()
                self._apply()
        elif chosen is a_fg:
            col = QColorDialog.getColor(QColor(self.cfg['fg']), self, '字体颜色')
            if col.isValid():
                self.cfg['fg'] = col.name()
                self._apply()
        elif chosen is a_font:
            init = QFont() if not self._font else QFont(self._font)
            ok, font = QFontDialog.getFont(init, self, '选择字体')
            if ok:
                self._font = font.family()
                self.cfg['font'] = self._font
                self._apply()
        elif chosen in size_acts:
            self.cfg['scale'] = size_acts[chosen]
            self._apply()
        elif chosen is a_reset:
            self.cfg = dict(DEFAULT_CFG)
            self._apply()

    def _apply(self):
        self._push_style()
        self._save_cfg()
        self._n = -1                     # 卡片尺寸可能变了 -> 重算窗口高度
        self._fit(self._count)

    # ---- 配置持久化 ----
    def _load_cfg(self):
        try:
            with open(CONFIG, encoding='utf-8') as f:
                c = json.load(f)
            return {'bg': c.get('bg', DEFAULT_CFG['bg']),
                    'fg': c.get('fg', DEFAULT_CFG['fg']),
                    'scale': float(c.get('scale', 1.0)),
                    'font': c.get('font', '')}
        except Exception:
            return dict(DEFAULT_CFG)

    def _save_cfg(self):
        try:
            with open(CONFIG, 'w', encoding='utf-8') as f:
                json.dump(self.cfg, f)
        except Exception:
            pass

    def _apply_best_view(self):
        try:
            scr = QApplication.primaryScreen().availableGeometry()
        except Exception:
            self.move(80, 80)
            return
        w = 300
        self.resize(w, 400)
        self.move(scr.x() + scr.width() - w - 24, scr.y() + 48)

    def open_folder(self):
        try:
            os.startfile(EXE_DIR)
        except Exception:
            pass

    def open_new(self):
        start = 'D:\\project' if os.path.isdir('D:\\project') else os.path.expanduser('~')
        try:
            subprocess.Popen(['wt.exe', '-w', 'new', '-d', start, 'cmd', '/k', 'claude'])
            return
        except Exception:
            pass
        try:
            subprocess.Popen('cmd /k claude', cwd=start, creationflags=CREATE_NEW_CONSOLE)
        except Exception:
            pass

    def toggle_pin(self):
        self.pinned = not self.pinned
        f = self.windowFlags()
        f = (f | Qt.WindowStaysOnTopHint) if self.pinned else (f & ~Qt.WindowStaysOnTopHint)
        self.setWindowFlags(f)
        self.pin_btn.setText('📌' if self.pinned else '📍')
        self.show()

    # ---- 卡片拖出坞: Python 接管, 16ms 心跳跟手 claude 窗口 ----
    def _drag_start(self, hwnd, x, y):
        self._drag_hwnd = int(hwnd)
        self._drag_offset = (int(x), int(y))            # 鼠标点对窗口左上角的初始偏移
        # 让坞不抢前台, 但保持置顶视觉(不被遮挡)
        try:
            # SWP_NOSIZE|SWP_NOZORDER|SWP_NOOWNERZORDER = 0x0005
            user32.SetWindowPos(int(hwnd), 0, int(x) - 80, int(y) - 20, 0, 0, 0x0005)
        except Exception:
            pass

    def _drag_outside(self, hwnd, x, y):
        # 启动 16ms 跟手定时器
        if not hasattr(self, '_drag_timer') or self._drag_timer is None:
            self._drag_timer = QTimer(self)
            self._drag_timer.timeout.connect(self._drag_follow)
        if not self._drag_timer.isActive():
            self._drag_timer.start(16)
        self._drag_hwnd = int(hwnd)
        # 记录偏移: 鼠标相对于窗口客户区的位置(这样拖出去时窗口不会跳)
        try:
            r = RECT(); user32.GetWindowRect(hwnd, ctypes.byref(r))
            self._drag_offset = (int(x) - r.left, int(y) - r.top)
            # 立刻把小窗口尺寸保存下来, 之后只移动不重新设尺寸
            self._drag_wh = (r.right - r.left, r.bottom - r.top)
        except Exception:
            self._drag_offset = (40, 20)
            self._drag_wh = (800, 480)
        self._drag_follow()

    def _drag_follow(self):
        if not getattr(self, '_drag_hwnd', 0):
            return
        # 用 ctypes GetCursorPos 取真实全屏坐标(跨窗口不丢)
        class Pt(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = Pt()
        user32.GetCursorPos(ctypes.byref(pt))
        ox, oy = self._drag_offset
        try:
            # SWP_NOSIZE|SWP_NOZORDER = 0x0005
            user32.SetWindowPos(self._drag_hwnd, 0, pt.x - ox, pt.y - oy, 0, 0, 0x0005)
        except Exception:
            pass

    def _drag_return(self):
        # 用户拖回坞内: 停掉跟手, 让窗口回原位
        if hasattr(self, '_drag_timer') and self._drag_timer:
            self._drag_timer.stop()
            self._drag_timer = None

    def _drag_drop(self, hwnd, x, y):
        # 坞外松手: 停止跟手, 窗口已停在鼠标松开点
        if hasattr(self, '_drag_timer') and self._drag_timer:
            self._drag_timer.stop()
            self._drag_timer = None

    def _drag_end(self, in_dock, x, y):
        # 坞内松手重排: 状态清理
        self._drag_hwnd = 0

    # ---- 顶栏拖动 ----
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < MARGIN + HEADER_H + 6:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    # ---- 跨屏重绘 ----
    def showEvent(self, e):
        if not self._styled:
            self._styled = True
            try:                              # Win11 原生圆角(不靠半透明, 网页保持锐利)
                pref = ctypes.c_int(2)        # DWMWCP_ROUND
                dwmapi.DwmSetWindowAttribute(int(self.winId()), 33,
                                             ctypes.byref(pref), ctypes.sizeof(pref))
            except Exception:
                pass
            wh = self.windowHandle()
            if wh is not None:
                wh.screenChanged.connect(self._on_screen_changed)
        super().showEvent(e)

    def moveEvent(self, e):
        # 去掉了 self.update() / self.panel.update(): 拖拽时每秒百次,
        # 全窗重绘的中间帧会被 QtWebEngine 拿出来说"闪一下".
        super().moveEvent(e)

    def _on_screen_changed(self, _scr):
        # 屏变信号可能连续触发多次, 用 single-shot 去抖,
        # 让 resize(w+1)/resize(w) 只在最后一次触发时跑, 避免连闪.
        if not hasattr(self, '_scr_timer') or self._scr_timer is None:
            self._scr_timer = QTimer(self)
            self._scr_timer.setSingleShot(True)
            self._scr_timer.timeout.connect(self._on_screen_changed_apply)
        self._scr_timer.start(50)

    def _on_screen_changed_apply(self):
        w, h = self.width(), self.height()
        self.resize(w, h + 1)
        self.resize(w, h)


def main():
    # 高 DPI 全栈开启 -> 让 QtWebEngine 按屏幕真 DPI(如 1.5) 渲染, 修复文字发虚
    try:     # Qt6
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except AttributeError:
        try:  # Qt5 兜底
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        except Exception:
            pass
    try:
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    except Exception:
        pass
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    dock = Dock()
    dock.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
