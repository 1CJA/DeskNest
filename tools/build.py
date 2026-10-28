"""Reproducible Windows onedir build. Run with the project Python interpreter."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.licenses import collect
from desknest import __version__

root = Path(__file__).resolve().parents[1]
os.chdir(root)
# Each release gets its own directory, so building cannot overwrite a running older app.
release_root = root / "dist" / __version__
app_dir = release_root / "DeskNest"
os.environ["PYINSTALLER_CONFIG_DIR"] = str(root/"build"/"pyinstaller-cache")
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
    "--name", "DeskNest", "--distpath", str(release_root), "--exclude-module", "PySide6.QtWebEngineCore",
    "--exclude-module", "PySide6.QtWebEngineWidgets", "--exclude-module", "PySide6.QtQml",
    "--exclude-module", "PySide6.QtQuick", "--exclude-module", "PySide6.QtPdf",
    "--exclude-module", "win32ui", "--hidden-import", "win32com.shell.shell",
    "--hidden-import", "pythoncom", "main.py"], check=True)
shutil.copy2(root/"README.md", app_dir/"README.md")
shutil.copy2(root/"LICENSE", app_dir/"LICENSE")
shutil.copy2(root/"CHANGELOG.md", app_dir/"CHANGELOG.md")
shutil.copytree(root/"docs", app_dir/"docs", dirs_exist_ok=True)
collect(app_dir/"licenses")
archive = shutil.make_archive(str(root/"dist"/f"DeskNest-{__version__}-windows-x64"),
                             "zip", release_root, "DeskNest")
print(f"Executable: {app_dir / 'DeskNest.exe'}")
print(f"Archive: {archive}")
