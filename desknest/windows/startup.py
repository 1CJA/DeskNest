import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_VALUE_NAME = "DeskNest"

def startup_command():
    executable = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([str(executable), "--minimized"])
    pythonw = executable.with_name("pythonw.exe")
    script = Path(__file__).resolve().parents[2] / "main.py"
    return subprocess.list2cmdline([str(pythonw if pythonw.exists() else executable), str(script), "--minimized"])

def set_startup_enabled(enabled):
    if sys.platform != "win32":
        raise OSError("开机启动仅支持 Windows。")
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, APP_VALUE_NAME)
            except FileNotFoundError:
                pass

def is_startup_enabled():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            command, _ = winreg.QueryValueEx(key, APP_VALUE_NAME)
            return command == startup_command()
    except OSError:
        return False
