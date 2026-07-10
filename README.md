# Claude Code Dock — Web 3D Edition (V2.7)

A small Windows floating dock I put together for myself, for counting and quickly switching between the Claude Code windows I have open. This is the **Web 3D** branch — the front-end is rendered by QtWebEngine (HTML/CSS), with the data side coming from the Python scanner in `python坞V1.08`. Personally I find it quite handy to use; when I have 6–8 sessions running, Alt-Tab gets old fast.


## What it does

- Scans all visible Claude Code console windows and shows them as numbered, stacked cards.
- Per-card status light (idle vs. busy), session title, PID, context %, and token count.
- Click a card → focuses that window (even through other apps' foreground locks).
- CSS-driven 3D parallax — the card content tilts as the cursor approaches, and a soft "spotlight" follows the pointer.
- Scrolling switches between cards; right-click opens settings (background colour, text colour, font, card size).

## What's new in this version (V2.7)

- "Font…" added to the right-click menu — pick a single font for the whole dock (cards, PID, token, badges).
- Right-click the title bar now also opens the project's folder in Explorer.
- A small `V2.7` mark in the bottom-right corner.

## How it works (short version)

1. `claude_dock_web.py` is a PySide6 + QtWebEngine host. It points `SCANNER` at `python坞V1.08/claude_dock.py`.
2. Every 1.5 s the host launches `python ... --scan`, parses the JSON, and pushes it to the embedded web page over a `QWebChannel`.
3. `dashboard.html` is the UI — CSS perspective container, radial-gradient spotlight on hover, a marquee for long titles, and a small WebChannel bridge so card clicks call back into Python to focus the underlying Windows console.

That's it. There is no remote / cloud side; everything runs locally.

## Requirements

- Windows 10 / 11
- Python 3.9+
- `pip install PySide6 pillow`

## Run

Double-click `启动.bat`, or from a shell:

```
python  claude_dock_web.py
```

The dock pins itself to the top-right of the primary monitor on first launch and stays on top. If you don't see anything, the WebEngine page may still be initialising — give it a second or two.

## Known limitations

- Some titles get cut off in the card; long sessions scroll on hover. This was an intentional compromise for card height.
- DPI handling between monitors of different scale factors can still cause a brief paint glitch on first cross-screen drag. The Python scan side is patched in `python坞V1.08`; the web front-end inherits the same partial fix.
- Windows only; no plans for macOS / Linux right now.

## License

MIT. See `LICENSE` if/when it's included — for now, do whatever you want with this code.

---

## 中文说明（给国内朋友）

这是 `claude_dock` 的 **Web 3D 版**，基于 PySide6 + QtWebEngine。`python坞V1.08` 负责扫窗口拿数据，网页负责把卡片画得漂亮。

V2.7 在 V2.6 之上补了两个细节：右键菜单加了"字体…"（一次性改全坞字体），标题栏右键能直接打开项目文件夹，右下角有个小小的 V2.7 标识。

迭代过 V2.0 ~ V2.7 共 8 个版本，每代基本是"修一个细节 + 一个小功能"，节奏不赶，所以日常用着还顺。**纯本地、零网络请求、所有数据自己管**，介意隐私的朋友应该会喜欢这一点。

8 张卡片是常态——Alt-Tab 切 6+ 个 Claude Code 窗口确实烦，所以做这个。喜欢就拿去用，有问题/LGTM 都在 Issues 里聊。

> 备注：仓库里不包含 python坞V1.08/claude_dock.py, 它作为外部扫描器被调用; 如果想本地完整运行, 把那个版本的文件放到仓库外的 python坞V1.08/ 目录下即可。
