# 第三方组件

DeskNest 使用动态加载的 Qt/PySide6 组件，发布目录保留其 DLL，用户可替换兼容版本。

- Python 3.12.10：Python Software Foundation License。源码与许可：https://www.python.org/downloads/release/python-31210/
- PySide6-Essentials / shiboken6 6.12.0：Qt for Python，包含 LGPL/GPL/商业许可选项；本项目使用的 Qt Widgets、Core、Gui 以所附许可证为准。项目：https://code.qt.io/cgit/pyside/pyside-setup.git/
- Qt 6.12：对应模块和第三方许可证随 PySide6 分发；源码：https://code.qt.io/cgit/qt/
- pywin32 312：Python Software Foundation 兼容许可，详见项目 LICENSE。源码：https://github.com/mhammond/pywin32
- SQLite：Public Domain，https://www.sqlite.org/copyright.html
- PyInstaller 6.22.3：GPL 带分发例外，用作构建工具；https://pyinstaller.org/

发布包的 licenses 目录包含本机安装分发包提供的许可证副本。DeskNest 自身源码采用根目录 LICENSE 中的 MIT License；第三方组件仍适用各自许可证。

Qt/PySide6 的 LGPL-3.0 与其引用的 GPL-3.0 完整文本位于 docs/licenses。DeskNest 未修改 Qt/PySide6 源码，具体版本可通过上述官方源码仓库的版本标签取得。
