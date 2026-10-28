from __future__ import annotations
import os
from pathlib import Path

APP_NAME = "DeskNest"
LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
# Useful for portable mode and isolated verification; normal installs use LocalAppData.
APP_DATA_DIR = Path(os.environ.get("DESKNEST_DATA_DIR", LOCAL_APP_DATA / APP_NAME)).resolve()
BACKUP_DIR = APP_DATA_DIR / "backups"
ICON_CACHE_DIR = APP_DATA_DIR / "icons"
DATABASE_PATH = APP_DATA_DIR / "desknest.db"

def ensure_app_dirs():
    for path in (APP_DATA_DIR, BACKUP_DIR, ICON_CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)
