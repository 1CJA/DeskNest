from __future__ import annotations
import logging
import os
from pathlib import Path
from desknest.models import DesktopItem
from desknest.windows.desktop import desktop_paths

class DesktopScanner:
    def __init__(self):
        self.warnings = []

    def desktop_paths(self):
        return desktop_paths()

    def scan(self):
        self.warnings = []
        results, seen = [], set()
        for directory in self.desktop_paths():
            try:
                entries = sorted(directory.iterdir(), key=lambda p: p.name.casefold())
            except OSError as error:
                self.warnings.append(f"无法读取 {directory}: {error}")
                continue
            for entry in entries:
                if entry.name.casefold() in ("desktop.ini", "thumbs.db") or entry.name.startswith(("~$", ".")):
                    continue
                try:
                    key = os.path.normcase(str(entry.absolute()))
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append(self.from_path(entry))
                except OSError as error:
                    self.warnings.append(f"无法读取 {entry.name}: {error}")
        return results

    @staticmethod
    def from_path(path):
        path = Path(path).absolute()
        kind = "folder" if path.is_dir() else (
            "shortcut" if path.suffix.lower() == ".lnk" else
            "web" if path.suffix.lower() == ".url" else "file")
        name = path.stem if kind in ("shortcut", "web") else path.name
        # Launch the original .lnk to preserve arguments, working directory and elevation.
        return DesktopItem(None, name, str(path), kind, source_path=str(path))
