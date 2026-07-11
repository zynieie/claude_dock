# Claude Code Dock — Web 3D Edition (V2.9)

A small Windows floating dock for counting and quickly switching between Claude Code sessions.

**Current version: V2.9** — first fully-packaged release. Runs as a single-folder `ClaudeDock.exe` with **Windows system tray icon**, no Python required.

## What's new in V2.9

- 🖥 **Windows 系统托盘** — ◐ 图标常驻；右键菜单（显示坞/隐藏坞/卡片大小/开机启动/关于/退出）；双击切显隐
- 📦 **单 EXE 打包** — PyInstaller onedir 产物，~152 MB（QtWebEngine 占大头），双击即用，零 Python 依赖
- 🚀 **开机自启** — `HKCU\...\Run\ClaudeDock` 注册表项（无需管理员）
- 🛠 **scanner 内联** — 从 `python坞V1.08/claude_dock.py` 抽纯函数到 `scanner_core.py`，主坞直接 import 调用（不再走 subprocess）
- 🐛 **修复打包后路径失效** — 双路径 `HERE`（EXE 同级，可写配置）+ `ASSETS`（`_MEIPASS`，只读资源）
- 🎯 **关闭语义改造** — 点 ✕ 不退出，仅隐藏到托盘；托盘菜单"退出"才真退出

## Download & Install

### 方式 1：下载 Release zip（推荐）

1. 打开 https://github.com/zynieie/claude_dock/releases 下载最新的 `ClaudeDock-Web-V2.9-win-x64.zip`
2. 解压到任意目录（建议英文路径，如 `C:\ClaudeDock\`）
3. 双击 `ClaudeDock.exe` 即可运行

> 首次启动 Windows Defender 可能弹"未知应用"警告 → 选择"详细信息 → 仍要运行"

### 方式 2：Python 源码运行（开发者）

```bash
pip install PySide6 psutil pillow
git clone https://github.com/zynieie/claude_dock.git
cd claude_dock
python  tray_main.py     # GUI 模式
python  tray_main.py --scan    # CLI: 打印 session JSON
```

> 源码模式需自行提供 `python坞V1.08/claude_dock.py` 作为参考实现（v1.08+ 包含完整 scanner 逻辑；本仓库 `scanner_core.py` 是从该文件抽取的纯函数版）。

### 方式 3：自己打包 EXE

```bash
python -m pip install pyinstaller
python make_icon.py
python -m PyInstaller --clean --noconfirm tray_main.spec
# 产物在 dist/ClaudeDock/
```

## 功能特性

- 🎴 **3D 卡片**：编号 + 跑马灯标题 + 状态灯 + 实时 token / context%
- 🖱 **拖出坞跟手**：长按卡片拖出坞外，松开停在落点；拖回坞内卡片归位
- ⌨️ **滚轮切换**：悬停卡片滚轮上/下切窗口，自动 focus
- ⚙️ **右键设置**：背景色 / 字体色 / 字体 / 卡片大小（小/标准/大/特大）
- 🔁 **1.5s 实时刷新**：Claude Code 开/关、状态变化自动同步
- 🪟 **跨屏不黑屏**：双屏不同 DPI 也能稳定渲染

## 文件结构

```
claude_dock/                      # 本仓库
├── README.md                     # 本文件
├── CHANGELOG.md                  # 更新日志
├── LICENSE                       # MIT
├── .gitignore
├── screenshot.jpg                # 主界面截图
├── claude_dock_web.py            # 原始 Python 入口（V2.7 兼容）
├── dock_tray.py                  # 托盘友好版（V2.9 改造）
├── tray_main.py                  # V2.9 入口 + 托盘
├── scanner_core.py               # 扫描器纯函数（从 python坞V1.08 抽取）
├── make_icon.py                  # dock.ico 生成
├── tray_main.spec                # PyInstaller 配置
├── build.bat                     # 一键打包脚本
├── dock.ico                      # 多分辨率图标（6 档）
├── dashboard.html                # 3D 卡片 UI（QtWebEngine 渲染）
├── 启动.bat                       # 源码模式启动脚本（中文）
└── 拖拽设计.md                    # 拖拽架构设计文档
```

## 系统要求

| 项目 | 要求 |
|------|------|
| OS | Windows 10 (1809+) / Windows 11 |
| 架构 | x64 (Intel/AMD) |
| 内存 | 至少 200MB 可用 |
| 磁盘 | 至少 500MB（含 QtWebEngine 解压） |
| Claude | `claude.exe` 须在 PATH 中（Claude Code CLI 标准安装即可） |

## 常见问题

### 启动后白屏
首次启动需要 5-10 秒初始化 QtWebEngine。持续白屏检查 `_internal/PySide6/QtWebEngineProcess.exe` 是否存在。

### Windows Defender 报毒
PyInstaller 打包的 EXE 无代码签名，Defender 误报常见。右键 EXE → 属性 → 解除锁定，或在 Defender 历史记录中允许。

### 解压到中文路径打不开
把文件夹改名为英文（如 `C:\ClaudeDock\`）再试。

## License

MIT. See `LICENSE`.

---

## 中文说明

这是 `claude_dock` 的 **Web 3D 版**，基于 PySide6 + QtWebEngine。

**V2.9** 是首个完全打包的发布版：单文件夹 EXE + Windows 系统托盘常驻，无需装 Python 即可在任意 Win10/Win11 电脑运行。源码结构也保留了 Python 模式入口（`python tray_main.py`），开发调试友好。

> **隐私**：纯本地、零网络请求、所有数据自己管，介意隐私的朋友应该会喜欢这一点。

喜欢就拿去用，有问题/LGTM 都在 [Issues](https://github.com/zynieie/claude_dock/issues) 里聊。
