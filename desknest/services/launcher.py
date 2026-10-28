import os
from pathlib import Path
from desknest.models import DesktopItem

class Launcher:
    def launch(self, item: DesktopItem):
        path = Path(item.path)
        if not path.exists():
            raise FileNotFoundError(f"原始项目已移动或不存在：{path}\n请重新扫描，或从 DeskNest 移除失效引用。")
        if os.name != "nt":
            raise OSError("启动功能仅支持 Windows。")
        # Never substitute the shortcut's target: it loses args and working directory.
        os.startfile(str(path))

    def reveal(self, item):
        path = Path(item.path)
        parent = path if path.is_dir() else path.parent
        if not parent.exists():
            raise FileNotFoundError("原文件所在位置已不存在。")
        os.startfile(str(parent))
