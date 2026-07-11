# Changelog

All notable changes to Claude Dock will be documented in this file.

## [2.9.0] - 2026-07-10

### 首个 Windows 可执行发布版
- 新增 **PyInstaller 打包**：单 `ClaudeDock.exe` + `_internal/` 文件夹，零依赖双击即用
- 新增 **Windows 系统托盘**：◐ 图标常驻，右键菜单（显示/隐藏/卡片大小/开机启动/关于/退出）
- 新增 **开机自启**：`HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run\ClaudeDock` 注册表项（无需管理员权限）
- 新增 **关闭语义改造**：点 ✕ 不退出，仅隐藏到托盘；托盘菜单"退出"才真退出

### 重构
- **scanner 内联**：把 `python坞V1.08/claude_dock.py` 的纯函数搬到 `scanner_core.py`，主坞直接 import 调用（**不再 subprocess**）
- 扫描器路径不再依赖相对目录 `../python坞V1.08/`，彻底解决打包后路径失效问题

### 修复
- 修复打包后 `dashboard.html` 找不到的问题（双路径：frozen 时读 `_MEIPASS`、未打包时读 `__file__` 同级）
- 修复打包后用户配置 `dock_web_config.json` 不可写的问题（frozen 时写 EXE 同级，不是 `_MEIPASS`）
- 修复 `QAction` import 错误（PySide6 属于 QtGui，非 QtWidgets）

### 产物
- `ClaudeDock.exe`（~1.1 MB）
- `_internal/`（~366 MB，含 Qt6 DLLs、QtWebEngine Chromium、Python runtime）
- 总大小：~367 MB（QtWebEngine 占大头）
- 兼容：Windows 10 (1809+) / Windows 11 x64

## [2.8] - 2026-07-05

### 新增
- 坞内拖拽重排：长按拖动，抬起幽灵卡片 + 蓝色插入线
- 卡片拖出坞：16ms 心跳跟手真实 Claude 窗口

## [2.7] 及更早

详见 git log 或 `D:\project\claude_dock\拖拽设计.md`

---

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)