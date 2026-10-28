from pathlib import Path
import os

def desktop_paths():
    """Shell locations respect redirected/OneDrive desktops; no guessed second desktop."""
    if os.name == "nt":
        from win32com.shell import shell, shellcon
        paths = [Path(shell.SHGetFolderPath(0, kind, None, 0))
                 for kind in (shellcon.CSIDL_DESKTOPDIRECTORY, shellcon.CSIDL_COMMON_DESKTOPDIRECTORY)]
    else:
        paths = [Path.home() / "Desktop"]
    return list(dict.fromkeys(paths))
