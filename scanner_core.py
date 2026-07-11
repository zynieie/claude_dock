# -*- coding: utf-8 -*-
"""
Claude Dock 扫描器核心（纯函数版）
================================
从 `python坞V1.08/claude_dock.py` 抽取的纯函数，**无 GUI 依赖**。
打包进 PyInstaller EXE 后，主坞直接 `import scanner_core` 调用，不再走 subprocess。

职责：
- 枚举所有 claude.exe 控制台，读取标题 + context%
- 枚举所有可见窗口（hwnd + title），与控制台标题匹配
- 从 `~/.claude/projects/<encoded>/<jsonl>` 末尾读取最后一次 usage.token
- 输出标准 session 列表：{hwnd, pid, title, clean, status, ctx, ctxtok}

调用方式：
- 主坞：`scanner.scan_sessions()`（在 QThread 里跑，避免阻塞 UI）
- 命令行：`python scanner_core.py --scan`（输出 JSON，便于单测）
"""
import sys
import os
import io
import re
import json
import glob
import ctypes
from ctypes import wintypes
from datetime import datetime

# Windows 默认 GBK，打印中文乱码 → 强制 UTF-8（防御性，万一有人 --scan 直跑）
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower().startswith('gb'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype = ctypes.c_bool
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = ctypes.c_bool
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
kernel32.AttachConsole.argtypes = [wintypes.DWORD]
kernel32.AttachConsole.restype = ctypes.c_bool
kernel32.FreeConsole.restype = ctypes.c_bool
kernel32.GetConsoleTitleW.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
kernel32.GetConsoleTitleW.restype = ctypes.c_uint

IDLE_GLYPHS = '✳✻✶✷✸✹✺*'


class COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]


class SMALL_RECT(ctypes.Structure):
    _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short),
                ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]


class CSBI(ctypes.Structure):
    _fields_ = [("dwSize", COORD), ("dwCursorPosition", COORD),
                ("wAttributes", ctypes.c_ushort), ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def classify(title):
    if not title:
        return 'idle', ''
    c = title[0]
    if c in IDLE_GLYPHS:
        status = 'idle'
    elif 0x2800 <= ord(c) <= 0x28FF:
        status = 'busy'
    elif ord(c) >= 0x2000:
        status = 'idle'
    else:
        return 'idle', title
    return status, title[1:].strip()


def read_console_title(pid):
    kernel32.FreeConsole()
    if not kernel32.AttachConsole(pid):
        return None
    buf = ctypes.create_unicode_buffer(1024)
    n = kernel32.GetConsoleTitleW(buf, 1024)
    kernel32.FreeConsole()
    return buf.value if n else ''


def read_console_ctx(pid):
    """读控制台可见缓冲区, 抓 context% (作为占用条)。失败返回 None。"""
    kernel32.FreeConsole()
    if not kernel32.AttachConsole(pid):
        return None
    ctx = None
    try:
        h = kernel32.CreateFileW("CONOUT$", 0xC0000000, 0x3, None, 3, 0, None)
        if h and h != -1 and h != 0xFFFFFFFFFFFFFFFF:
            info = CSBI()
            if kernel32.GetConsoleScreenBufferInfo(h, ctypes.byref(info)):
                w = info.dwSize.X
                buf = ctypes.create_unicode_buffer(w)
                got = wintypes.DWORD(0)
                rows = []
                for y in range(info.srWindow.Top, info.srWindow.Bottom + 1):
                    if kernel32.ReadConsoleOutputCharacterW(h, buf, w, COORD(0, y),
                                                            ctypes.byref(got)):
                        rows.append(buf[:got.value])
                mc = re.search(r'(\d+)\s*%\s*context', "\n".join(rows), re.I)
                if mc:
                    ctx = int(mc.group(1))
            kernel32.CloseHandle(h)
    except Exception:
        pass
    kernel32.FreeConsole()
    return ctx


def claude_console_titles():
    import psutil
    titles = {}
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] != 'claude.exe':
            continue
        try:
            t = read_console_title(p.info['pid'])
        except Exception:
            t = None
        if t:
            titles.setdefault(t, p.info['pid'])
    return titles


def visible_windows():
    out = []

    def _cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value:
                out.append((int(hwnd), buf.value))
        return True

    cb = EnumWindowsProc(_cb)
    user32.EnumWindows(cb, 0)
    return out


def _enc_proj(cwd):
    return re.sub(r'[^A-Za-z0-9]', '-', cwd)


def _iso(s):
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
    except Exception:
        return None


def _session_info(path):
    """(起始时间, 当前上下文token)。头读起始(扫前若干行), 尾读最后一次 usage。"""
    start, ctx = None, 0
    try:
        with open(path, encoding='utf-8') as f:
            for _ in range(12):                 # 前几行里找首个 timestamp
                line = f.readline()
                if not line:
                    break
                try:
                    ts = json.loads(line).get('timestamp')
                except Exception:
                    ts = None
                if ts:
                    start = _iso(ts)
                    if start:
                        break
        with open(path, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 262144))
            tail = f.read().decode('utf-8', 'replace')
        for line in reversed(tail.splitlines()):
            try:
                o = json.loads(line)
            except Exception:
                continue
            m = o.get('message')
            u = m.get('usage') if isinstance(m, dict) else None
            if isinstance(u, dict):
                c = (u.get('input_tokens', 0) or 0) + (u.get('cache_read_input_tokens', 0) or 0) \
                    + (u.get('cache_creation_input_tokens', 0) or 0)
                if c:
                    ctx = c
                    break
    except Exception:
        pass
    return start, ctx


def attach_ctxtok(sessions):
    """按 进程启动时间<->会话起始时间 贪心 1:1 配对, 给每个窗口填 ctxtok。"""
    import psutil
    from collections import defaultdict
    home = os.path.expanduser('~')
    groups = defaultdict(list)
    for s in sessions:
        try:
            p = psutil.Process(s['pid'])
            s['_ct'] = p.create_time()
            proj = os.path.join(home, '.claude', 'projects', _enc_proj(p.cwd()))
        except Exception:
            s['ctxtok'] = 0
            continue
        groups[proj].append(s)
    for proj, ss in groups.items():
        files = glob.glob(os.path.join(proj, '*.jsonl'))
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        cand = []
        for p in files[:15]:
            st, ctx = _session_info(p)
            if st is not None and ctx:
                cand.append((p, st, ctx))
        pairs = []
        for s in ss:
            for c in cand:
                pairs.append((abs(s.get('_ct', 0) - c[1]), id(s), s, c))
        pairs.sort(key=lambda x: x[0])
        used_s, used_f = set(), set()
        for _d, sid, s, c in pairs:
            if sid in used_s or c[0] in used_f:
                continue
            s['ctxtok'] = c[2]
            used_s.add(sid)
            used_f.add(c[0])
    for s in sessions:
        s.pop('_ct', None)
        s.setdefault('ctxtok', 0)


def scan_sessions():
    """主入口：返回 session 列表，每项 {hwnd, pid, title, clean, status, ctx, ctxtok}"""
    import psutil
    ctitles = claude_console_titles()
    wins = visible_windows()
    used = set()
    sessions = []

    def _emit(pid, hwnd, wtitle):
        used.add(hwnd)
        status, clean = classify(wtitle)
        sessions.append({'hwnd': hwnd, 'pid': pid, 'title': wtitle,
                         'clean': clean or wtitle, 'status': status,
                         'ctx': read_console_ctx(pid)})

    remaining = dict(ctitles)
    for ctitle in list(remaining):
        pid = remaining[ctitle]
        for hwnd, wtitle in wins:
            if hwnd not in used and wtitle == ctitle:
                _emit(pid, hwnd, wtitle)
                del remaining[ctitle]
                break
    for ctitle in list(remaining):
        pid = remaining[ctitle]
        _, cclean = classify(ctitle)
        if not cclean:
            continue
        for hwnd, wtitle in wins:
            if hwnd not in used and classify(wtitle)[1] == cclean:
                _emit(pid, hwnd, wtitle)
                break
    attach_ctxtok(sessions)
    return sessions


if __name__ == '__main__' and '--scan' in sys.argv:
    print(json.dumps(scan_sessions(), ensure_ascii=False))
    sys.exit(0)