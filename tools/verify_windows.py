"""Native smoke check. Uses only workspace sample files, never moves desktop items."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
import subprocess

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
import win32com.client

from desknest.storage.database import Database
from desknest.services.scanner import DesktopScanner
from desknest.services.launcher import Launcher
from desknest.ui.main_window import MainWindow

root = Path(__file__).resolve().parents[1] / "test-data" / "native"
root.mkdir(parents=True, exist_ok=True)
marker = root / "launch-ok.txt"
marker.unlink(missing_ok=True)
shortcut_path = root / "启动验证.lnk"
link = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(shortcut_path))
link.TargetPath = str(Path(os.environ["WINDIR"])/"System32"/"cmd.exe")
link.Arguments = '/d /c "echo DeskNest>launch-ok.txt"'
link.WorkingDirectory = str(root)
link.WindowStyle = 7
link.Save()
Launcher().launch(DesktopScanner.from_path(shortcut_path))
deadline = time.monotonic()+8
while not marker.exists() and time.monotonic() < deadline:
    time.sleep(.1)
if not marker.exists():
    raise RuntimeError("Shortcut launch did not preserve working directory / arguments")

app = QApplication([])
app.setStyle("Fusion")
db = Database(root/"ui.db")
db.initialize()
(root/"文档").mkdir(exist_ok=True)
(root/"会议记录.txt").write_text("DeskNest test", encoding="utf-8")
(root/"参考资料.url").write_text("[InternetShortcut]\nURL=https://example.com\n", encoding="utf-8")
items = [DesktopScanner.from_path(root/name) for name in
         ("启动验证.lnk","文档","会议记录.txt","参考资料.url")]
db.add_items(items, db.categories()[0].id)
first = db.items()[0]
db.update_item_flags(first.id, favorite=True, pinned=True)
window = MainWindow(db)
window.show()
report = {"real_shortcut_launch": True, "items":len(db.items()),
          "tray_available":bool(window.tray),
          "hotkey_registered":bool(window.hotkey and window.hotkey.registered)}

def finish():
    try:
        window.grab().save(str(root/"light.png"))
        db.set_setting("theme","dark")
        window._apply_theme()
        app.processEvents()
        window.grab().save(str(root/"dark.png"))
        db.set_setting("theme","light")
        (root/"report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        window._quit()
QTimer.singleShot(1000, finish)
raise SystemExit(app.exec())
