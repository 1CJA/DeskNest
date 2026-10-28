import ctypes
from ctypes import wintypes
import sys
from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, Signal

class _Filter(QAbstractNativeEventFilter):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def nativeEventFilter(self, event_type, message):
        if sys.platform == "win32" and message:
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == self.owner.HOTKEY_ID:
                self.owner.activated.emit()
                return True, 0
        return False, 0

class GlobalHotkey(QObject):
    activated = Signal()
    HOTKEY_ID = 0x4D53

    def __init__(self, parent=None):
        super().__init__(parent)
        self.registered = False
        self.filter = _Filter(self)
        if sys.platform == "win32":
            self.registered = bool(ctypes.windll.user32.RegisterHotKey(None, self.HOTKEY_ID, 0x4003, 0x20))
            if self.registered:
                QCoreApplication.instance().installNativeEventFilter(self.filter)

    def close(self):
        if self.registered:
            ctypes.windll.user32.UnregisterHotKey(None, self.HOTKEY_ID)
            QCoreApplication.instance().removeNativeEventFilter(self.filter)
            self.registered = False
