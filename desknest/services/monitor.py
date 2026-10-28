from __future__ import annotations

from PySide6.QtCore import QObject, QFileSystemWatcher, QTimer, Signal

from desknest.services.scanner import DesktopScanner


class DesktopMonitor(QObject):
    changed = Signal()

    def __init__(self, scanner: DesktopScanner, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(700)
        self._watcher.directoryChanged.connect(self._schedule_change)
        self._timer.timeout.connect(self.changed)
        paths = [str(path) for path in scanner.desktop_paths()]
        if paths:
            self._watcher.addPaths(paths)

    def _schedule_change(self) -> None:
        self._timer.start()

