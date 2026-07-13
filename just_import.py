import sys, os, tempfile

# 日志写到系统临时目录 (不依赖用户名/本机路径)
sys.stdout = open(os.path.join(tempfile.gettempdir(), 'just_import.log'), 'w', encoding='utf-8')
print("start", flush=True)
# 切到本脚本所在目录, 让 dashboard.html 与脚本同位置
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
print("Qt import OK", flush=True)
app = QApplication(sys.argv)
print("QApplication OK", flush=True)
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    print("WebEngine import OK", flush=True)
    v = QWebEngineView()
    print("view created", flush=True)
    v.load(f'file:///{os.path.abspath("dashboard.html")}')
    print("load called - entering event loop", flush=True)
    sys.exit(app.exec())
except Exception as e:
    print(f"WebEngine FAILED: {type(e).__name__}: {e}", flush=True)
    import traceback; traceback.print_exc()
    sys.exit(1)
