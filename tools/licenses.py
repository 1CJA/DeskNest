from pathlib import Path
import importlib.metadata as metadata
import shutil
import sys

def collect(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    python_license = Path(sys.base_prefix)/"LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, destination/"Python-LICENSE.txt")
    for name in ("PySide6-Essentials", "shiboken6", "pywin32"):
        dist = metadata.distribution(name)
        package_dir = destination / name
        package_dir.mkdir(exist_ok=True)
        (package_dir/"METADATA.txt").write_text((dist.read_text("METADATA") or ""), encoding="utf-8")
        for file in dist.files or []:
            if "license" in str(file).lower() or "copying" in str(file).lower():
                path = Path(dist.locate_file(file))
                if path.is_file():
                    target = package_dir / str(file).replace("/", "_").replace("\\", "_")
                    shutil.copy2(path, target)

if __name__ == "__main__":
    collect(Path(__file__).resolve().parents[1]/"dist"/"DeskNest"/"licenses")
