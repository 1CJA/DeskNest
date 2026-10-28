from __future__ import annotations
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

def main():
    parser = argparse.ArgumentParser(description="DeskNest desktop launcher")
    parser.add_argument("--data-dir", help="Override local data directory")
    parser.add_argument("--minimized", action="store_true")
    parser.add_argument("--smoke-test", metavar="REPORT", help="Start, render and exit with a JSON report")
    options = parser.parse_args()
    if options.data_dir:
        os.environ["DESKNEST_DATA_DIR"] = str(Path(options.data_dir).resolve())

    from PySide6.QtCore import QLockFile, QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    from desknest.config import APP_DATA_DIR, ensure_app_dirs
    from desknest.storage.database import Database
    from desknest.ui.main_window import MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("DeskNest")
    app.setOrganizationName("DeskNest")
    app.setApplicationDisplayName("DeskNest · 桌屿")
    app.setStyle("Fusion")
    database = None
    lock = None
    try:
        ensure_app_dirs()
        handler = RotatingFileHandler(APP_DATA_DIR / "desknest.log", maxBytes=1024*1024, backupCount=2, encoding="utf-8")
        logging.basicConfig(level=logging.INFO, handlers=[handler],
                            format="%(asctime)s %(levelname)s %(message)s", force=True)
        lock = QLockFile(str(APP_DATA_DIR / "instance.lock"))
        lock.setStaleLockTime(0)
        if not lock.tryLock(0):
            QMessageBox.information(None, "DeskNest", "DeskNest 已在运行，请从系统托盘或 Ctrl+Alt+Space 打开。")
            return 0
        database = Database()
        database.initialize()
        window = MainWindow(database, integrations=not bool(options.smoke_test))

        def exception_hook(kind, error, tb):
            logging.error("Unhandled UI error", exc_info=(kind, error, tb))
            QMessageBox.warning(window, "操作未完成", str(error))
        sys.excepthook = exception_hook

        if not options.minimized or not window.tray:
            window.show()

        if options.smoke_test:
            def finish():
                report = Path(options.smoke_test).resolve()
                report.parent.mkdir(parents=True, exist_ok=True)
                window.grab().save(str(report.with_suffix(".png")))
                report.write_text(json.dumps({"ok": True, "categories": len(database.categories()),
                    "items": len(database.items()), "title": window.windowTitle()}, ensure_ascii=False), encoding="utf-8")
                window._quit()
            QTimer.singleShot(600, finish)
        return app.exec()
    except Exception as error:
        logging.exception("Startup failed")
        if options.smoke_test:
            Path(options.smoke_test).write_text(json.dumps({"ok":False,"error":str(error)}), encoding="utf-8")
        else:
            QMessageBox.critical(None, "DeskNest 无法启动", f"{error}\n请检查数据目录是否可写。")
        return 1
    finally:
        if database:
            database.close()
        if lock:
            lock.unlock()

if __name__ == "__main__":
    raise SystemExit(main())
