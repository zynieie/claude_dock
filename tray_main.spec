# -*- mode: python ; coding: utf-8 -*-
"""
Claude Dock · PyInstaller spec
- 入口: tray_main.py
- 模式: onedir (启动快、杀软友好)
- 资源: dashboard.html + scanner_core.py 进 _MEIPASS
- 图标: dock.ico
"""
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# QtWebEngine 必需：collect 所有子模块（Core/Widgets/Channel）
hidden_webengine = (
    collect_submodules('PySide6.QtWebEngineCore')
    + collect_submodules('PySide6.QtWebEngineWidgets')
    + collect_submodules('PySide6.QtWebChannel')
)

a = Analysis(
    ['tray_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('dashboard.html', '.'),       # HTML 进 _MEIPASS
        ('scanner_core.py', '.'),     # 备用 import 路径
        ('dock.ico', '.'),            # 托盘图标 + 兜底（也嵌在 EXE 资源里）
    ],
    hiddenimports=[
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebChannel',
        'PySide6.QtPrintSupport',
        'PySide6.QtNetwork',
        'psutil',
        'shiboken6',
    ] + hidden_webengine,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 可选瘦身（~30-50MB），但不删 QtNetwork（scanner 用 urllib）
    excludes=[
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtSql',
        'PySide6.QtTest',
        'PySide6.QtBluetooth',
        'PySide6.QtNfc',
        'PySide6.QtPositioning',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtWebSockets',
        'PySide6.QtXml',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ClaudeDock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='dock.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ClaudeDock',
)