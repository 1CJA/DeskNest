from __future__ import annotations
import logging
import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QFileInfo, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QSystemTrayIcon, QVBoxLayout,
    QFileIconProvider, QFileDialog, QStyle)

from desknest import __version__
from desknest.services.backup import BackupService
from desknest.services.launcher import Launcher
from desknest.services.monitor import DesktopMonitor
from desknest.services.scanner import DesktopScanner
from desknest.ui.dialogs import ScanDialog, RestoreDialog, TYPES
from desknest.ui.theme import stylesheet
from desknest.ui.widgets import CategoryListWidget, ItemGrid, Background, FileDropLabel, ROLE
from desknest.windows.hotkey import GlobalHotkey
from desknest.windows.startup import is_startup_enabled, set_startup_enabled


class ScanWorker(QThread):
    resultReady = Signal(object, object)
    failed = Signal(str)

    def run(self):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            scanner = DesktopScanner()
            self.resultReady.emit(scanner.scan(), scanner.warnings)
        except Exception as error:
            logging.exception("Desktop scan failed")
            self.failed.emit(str(error))
        finally:
            pythoncom.CoUninitialize()


class MainWindow(QMainWindow):
    def __init__(self, database, integrations=True):
        super().__init__()
        self.database = database
        self.backups = BackupService(database)
        self.launcher = Launcher()
        self.current_category_id = None
        self.dark_mode = database.setting("theme", "light") == "dark"
        self._allow_close = False
        self._scan_worker = None
        self._icon_cache = {}
        self.icons = QFileIconProvider()
        self.setWindowTitle(f"DeskNest · 桌屿 {__version__}")
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.setMinimumSize(960, 620)
        self.resize(1180, 760)
        self._build()
        self.tray = None
        self.hotkey = None
        if integrations:
            self._build_tray()
            self.hotkey = GlobalHotkey(self)
            self.hotkey.activated.connect(self._show_window)
            self.monitor = DesktopMonitor(DesktopScanner(), self)
            self.monitor.changed.connect(self._desktop_changed)
        self.refresh()
        self._apply_theme()
        self.statusBar().showMessage("拖入桌面图标即可收纳 · 点击卡片启动 · Ctrl+Z 撤销")
        if self.hotkey and not self.hotkey.registered:
            self.statusBar().showMessage("Ctrl+Alt+Space 已被其他程序占用，可从托盘打开 DeskNest")

    def _button(self, text, callback, primary=False):
        button = QPushButton(text)
        if primary:
            button.setObjectName("primary")
        button.clicked.connect(callback)
        return button

    def _build(self):
        self.root = Background()
        self.root.filesDropped.connect(self._queue_file_import)
        layout = QVBoxLayout(self.root)
        layout.setContentsMargins(24, 22, 24, 12)
        layout.setSpacing(20)
        header = QHBoxLayout()
        brand = QLabel("DeskNest")
        brand.setObjectName("brand")
        header.addWidget(brand)
        subtitle = QLabel("桌屿")
        subtitle.setObjectName("muted")
        header.addWidget(subtitle)
        header.addSpacing(20)
        self.search = QLineEdit()
        self.search.setAcceptDrops(False)
        self.search.setObjectName("search")
        self.search.setPlaceholderText("搜索全部分区中的软件、文件与文件夹")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refresh_items)
        header.addWidget(self.search, 1)
        self.scan_button = self._button("扫描桌面", self._scan_desktop, True)
        header.addWidget(self.scan_button)
        self.menu_button = self._button("更多", self._settings_menu)
        header.addWidget(self.menu_button)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(20)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 16, 12, 12)
        heading = QHBoxLayout()
        heading.addWidget(QLabel("我的分区"))
        heading.addStretch()
        heading.addWidget(self._button("+", self._create_category))
        side.addLayout(heading)
        self.categories = CategoryListWidget()
        self.categories.itemSelectionChanged.connect(self._category_changed)
        # Defer mutations until Qt completes its drag/drop event.
        self.categories.itemDropped.connect(lambda i,c: QTimer.singleShot(0, lambda: self._move_item(i,c)))
        self.categories.categoryDropped.connect(lambda i,t: QTimer.singleShot(0, lambda: self._reorder_categories(i,t)))
        self.categories.filesDropped.connect(self._queue_file_import)
        self.categories.setToolTip("将桌面图标拖到分区即可收纳；拖到「全部项目」会收纳到第一个分区。")
        side.addWidget(self.categories, 1)
        tools = QHBoxLayout()
        tools.addWidget(self._button("重命名", self._rename_category))
        tools.addWidget(self._button("删除", self._delete_category))
        side.addLayout(tools)
        hint = QLabel("本地保存 · 无需登录")
        hint.setObjectName("muted")
        side.addWidget(hint)
        body.addWidget(sidebar)
        content = QVBoxLayout()
        row = QHBoxLayout()
        self.section_title = QLabel("全部项目")
        self.section_title.setObjectName("brand")
        row.addWidget(self.section_title)
        row.addStretch()
        self.count_label = QLabel()
        self.count_label.setObjectName("muted")
        row.addWidget(self.count_label)
        content.addLayout(row)
        self.empty = FileDropLabel("将桌面图标拖到这里，开始收纳。")
        self.empty.filesDropped.connect(self._queue_file_import)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setObjectName("muted")
        self.empty.setWordWrap(True)
        content.addWidget(self.empty, 1)
        self.item_list = ItemGrid()
        self.item_list.filesDropped.connect(self._queue_file_import)
        self.item_list.itemClicked.connect(lambda row: self._launch_item(row.data(ROLE)))
        self.item_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.item_list.customContextMenuRequested.connect(self._context_menu)
        self.item_list.reorderRequested.connect(lambda i,t: QTimer.singleShot(0, lambda: self._reorder_items(i,t)))
        content.addWidget(self.item_list, 1)
        body.addLayout(content, 1)
        layout.addLayout(body, 1)
        self.setCentralWidget(self.root)

        self.undo_action = QAction("撤销上次操作", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self._undo)
        self.addAction(self.undo_action)
        search_action = QAction(self)
        search_action.setShortcut(QKeySequence.StandardKey.Find)
        search_action.triggered.connect(self.search.setFocus)
        self.addAction(search_action)
        launch_action = QAction(self.item_list)
        launch_action.setShortcut(QKeySequence(Qt.Key.Key_Return))
        launch_action.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        launch_action.triggered.connect(lambda: self._launch_item(self.item_list.currentItem().data(ROLE))
                                       if self.item_list.currentItem() else None)
        self.item_list.addAction(launch_action)

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("DeskNest · 桌屿")
        self.tray_menu = QMenu(self)
        self.tray_menu.addAction("打开 DeskNest", self._show_window)
        self.tray_menu.addAction("扫描桌面", self._scan_desktop)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction("退出", self._quit)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(lambda reason: self._show_window()
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.tray.show()

    def _apply_theme(self):
        self.dark_mode = self.database.setting("theme", "light") == "dark"
        QApplication.instance().setStyleSheet(stylesheet(self.dark_mode))
        self.item_list.setProperty("dark", self.dark_mode)
        self.item_list.viewport().update()
        self.root.set_background(self.database.setting("background", ""), self.dark_mode)
        try:
            pixels = int(self.database.setting("icon_size", "48"))
        except ValueError:
            pixels = 48
        self.item_list.set_icon_size(min(80, max(32, pixels)))

    def refresh(self):
        if self.current_category_id and not self.database.category(self.current_category_id):
            self.current_category_id = None
        self.categories.blockSignals(True)
        self.categories.clear()
        row = QListWidgetItem("全部项目")
        row.setData(ROLE, 0)
        row.setFlags(row.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
        self.categories.addItem(row)
        selected = 0
        for index, category in enumerate(self.database.categories(), 1):
            row = QListWidgetItem(category.name)
            row.setData(ROLE, category.id)
            self.categories.addItem(row)
            if category.id == self.current_category_id:
                selected = index
        self.categories.setCurrentRow(selected)
        self.categories.blockSignals(False)
        self._refresh_items()
        label = self.database.undo_label()
        self.undo_action.setEnabled(bool(label))
        self.undo_action.setText("撤销：" + label if label else "暂无可撤销操作")

    def _refresh_items(self):
        query = self.search.text().strip()
        category = None if query else self.current_category_id
        items = self.database.items(category, query)
        self.item_list.clear()
        for item in items:
            row = QListWidgetItem(item.name)
            row.setData(ROLE, item.id)
            row.setData(ROLE+1, (item.is_pinned, item.is_favorite, TYPES.get(item.item_type, "文件")))
            row.setToolTip(item.path)
            if item.path not in self._icon_cache:
                self._icon_cache[item.path] = self.icons.icon(QFileInfo(item.path))
            row.setIcon(self._icon_cache[item.path])
            self.item_list.addItem(row)
        cat = self.database.category(category) if category else None
        self.section_title.setText("搜索结果" if query else cat.name if cat else "全部项目")
        self.count_label.setText(f"{len(items)} 个项目")
        self.empty.setText("没有找到匹配的项目\n试试其他关键词，或直接拖入桌面图标添加。" if query else
                           "将桌面图标拖到这里\n\n支持快捷方式、文件和文件夹，原文件保留在桌面。\n也可以点击「扫描桌面」批量选择。")
        self.empty.setVisible(not items)
        self.item_list.setVisible(bool(items))
        self.item_list.setDragEnabled(not query)

    def _category_changed(self):
        row = self.categories.currentItem()
        self.current_category_id = row.data(ROLE) or None if row else None
        self._refresh_items()

    def _mutate(self, callback, success="已保存"):
        try:
            result = callback()
            self.refresh()
            self.statusBar().showMessage(success, 6000)
            return result
        except Exception as error:
            self._show_error("操作失败", error)

    def _create_category(self):
        name, ok = QInputDialog.getText(self, "新建分区", "分区名称")
        if ok:
            category = self._mutate(lambda: self.database.create_category(name))
            if category:
                self.current_category_id = category.id
                self.refresh()

    def _selected_category(self):
        category = self.database.category(self.current_category_id)
        if not category:
            QMessageBox.information(self, "选择分区", "请先选择左侧的自定义分区。")
        return category

    def _rename_category(self):
        category = self._selected_category()
        if category:
            name, ok = QInputDialog.getText(self, "重命名分区", "名称", text=category.name)
            if ok:
                self._mutate(lambda: self.database.rename_category(category.id, name))

    def _delete_category(self):
        category = self._selected_category()
        if category and QMessageBox.question(self, "删除分区",
                f"删除「{category.name}」？项目将移至第一个保留的分区，可使用 Ctrl+Z 撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self._mutate(lambda: self.database.delete_category(category.id))

    def _reorder_categories(self, source, target):
        ids = [c.id for c in self.database.categories()]
        if source == target or source not in ids or target not in ids:
            return
        ids.remove(source)
        ids.insert(ids.index(target), source)
        self._mutate(lambda: self.database.reorder_categories(ids))

    def _reorder_items(self, source, target):
        if self.search.text().strip():
            return
        ids = [self.item_list.item(i).data(ROLE) for i in range(self.item_list.count())]
        if source not in ids or source == target:
            return
        ids.remove(source)
        ids.insert(ids.index(target) if target in ids else len(ids), source)
        self._mutate(lambda: self.database.reorder_items(ids), "顺序已保存，置顶项目优先显示")

    def _scan_desktop(self):
        self._show_window()
        if self._scan_worker and self._scan_worker.isRunning():
            return
        self.scan_button.setEnabled(False)
        self.statusBar().showMessage("正在扫描桌面…")
        self._scan_worker = ScanWorker(self)
        self._scan_worker.resultReady.connect(self._scan_ready)
        self._scan_worker.failed.connect(lambda text: self._show_error("扫描失败", OSError(text)))
        self._scan_worker.finished.connect(lambda: self.scan_button.setEnabled(True))
        self._scan_worker.start()

    def _scan_ready(self, found, warnings):
        known = {os.path.normcase(i.path) for i in self.database.items()}
        found = [i for i in found if os.path.normcase(i.path) not in known]
        if warnings:
            QMessageBox.warning(self, "部分目录无法读取", "\n".join(warnings))
        if not found:
            self.statusBar().showMessage("扫描完成，没有发现未收纳的项目", 6000)
            return
        dialog = ScanDialog(found, self.database.categories(), self)
        if self.current_category_id:
            dialog.category.setCurrentIndex(dialog.category.findData(self.current_category_id))
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._mutate(lambda: self.database.add_items(dialog.selected_items(), dialog.selected_category_id()),
                         "已收纳所选项目，原始文件仍保留在桌面")

    def _queue_file_import(self, paths, category_id=None):
        # Capture the destination before returning to the native drag loop.
        target = self.current_category_id if category_id is None else category_id
        QTimer.singleShot(0, lambda: self._import_paths(paths, target))

    def _import_paths(self, paths, category_id):
        try:
            category = (self.database.category(category_id) if category_id
                        else self.database.categories()[0])
            if category is None:
                raise ValueError("目标分区已不存在，请重新拖入。")
            items, errors = [], []
            for raw_path in paths:
                try:
                    path = Path(raw_path).absolute()
                    # Read metadata only; never resolve .lnk targets or move files.
                    path.stat()
                    items.append(DesktopScanner.from_path(path))
                except (OSError, ValueError) as error:
                    errors.append(f"{raw_path}: {error}")
            added = self.database.add_items(items, category.id)
            duplicates = len(items) - added
            if added:
                self.current_category_id = category.id
                self.search.clear()
            self.refresh()
            parts = [f"已收纳 {added} 个项目到「{category.name}」"]
            if duplicates:
                parts.append(f"{duplicates} 个已存在，保留原分类")
            if errors:
                parts.append(f"{len(errors)} 个无法读取")
            parts.append("原文件保留，可按 Ctrl+Z 撤销" if added else "原文件保留")
            self.statusBar().showMessage(" · ".join(parts), 10000)
            if errors:
                logging.warning("Some dropped paths could not be imported: %s", errors)
                detail = "\n".join(errors[:5])
                if len(errors) > 5:
                    detail += f"\n另有 {len(errors) - 5} 个项目无法读取，详见日志。"
                QMessageBox.warning(self, "部分项目未收纳",
                                    "以下项目不存在或无法读取，原文件未改动：\n\n" + detail)
        except Exception as error:
            self._show_error("拖入收纳失败", error)

    def _launch_item(self, item_id):
        item = self.database.item(item_id)
        if item:
            try:
                self.launcher.launch(item)
                self.statusBar().showMessage(f"已启动：{item.name}", 4000)
            except Exception as error:
                self._show_error("无法启动", error)

    def _move_item(self, item_id, category_id):
        self._mutate(lambda: self.database.update_item_category(item_id, category_id), "已移入分区")

    def _context_menu(self, position):
        row = self.item_list.itemAt(position)
        if not row:
            return
        item = self.database.item(row.data(ROLE))
        if not item:
            return
        menu = QMenu(self)
        launch = menu.addAction("启动")
        favorite = menu.addAction("取消收藏" if item.is_favorite else "收藏")
        pin = menu.addAction("取消置顶" if item.is_pinned else "置顶")
        moves = menu.addMenu("移至分区")
        mapping = {moves.addAction(c.name): c.id for c in self.database.categories()}
        reveal = menu.addAction("打开所在位置")
        menu.addSeparator()
        remove = menu.addAction("移除引用")
        chosen = menu.exec(self.item_list.viewport().mapToGlobal(position))
        if chosen == launch:
            self._launch_item(item.id)
        elif chosen == favorite:
            self._mutate(lambda: self.database.update_item_flags(item.id, favorite=not item.is_favorite))
        elif chosen == pin:
            self._mutate(lambda: self.database.update_item_flags(item.id, pinned=not item.is_pinned))
        elif chosen in mapping:
            self._move_item(item.id, mapping[chosen])
        elif chosen == reveal:
            try:
                self.launcher.reveal(item)
            except Exception as error:
                self._show_error("打开位置失败", error)
        elif chosen == remove:
            self._mutate(lambda: self.database.delete_item(item.id), "已移除引用，可按 Ctrl+Z 撤销")

    def _undo(self):
        self._mutate(self.database.undo, "已撤销上次操作")

    def _settings_menu(self):
        menu = QMenu(self)
        theme = menu.addAction("切换到浅色" if self.dark_mode else "切换到深色")
        size_menu = menu.addMenu("图标大小")
        sizes = {size_menu.addAction(label): size for label,size in (("小",32),("中",48),("大",72))}
        background = menu.addAction("选择背景图片…")
        clear_bg = menu.addAction("清除背景")
        startup = menu.addAction("开机启动")
        startup.setCheckable(True)
        startup.setChecked(is_startup_enabled())
        menu.addSeparator()
        menu.addAction(self.undo_action)
        backup = menu.addAction("立即备份")
        export = menu.addAction("导出备份…")
        restore = menu.addAction("恢复本地备份…")
        import_backup = menu.addAction("从文件恢复…")
        menu.addSeparator()
        quit_action = menu.addAction("退出 DeskNest")
        chosen = menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft()))
        try:
            if chosen == theme:
                self.database.set_setting("theme", "light" if self.dark_mode else "dark")
            elif chosen in sizes:
                self.database.set_setting("icon_size", str(sizes[chosen]))
            elif chosen == background:
                path, _ = QFileDialog.getOpenFileName(self, "选择背景", "", "图片 (*.png *.jpg *.jpeg *.bmp)")
                if path:
                    if QPixmap(path).isNull():
                        raise ValueError("图片无法读取。")
                    # Keep a private copy so moving the original image does not break the background.
                    target = self.database.path.parent / ("background" + Path(path).suffix.lower())
                    if Path(path).resolve() != target.resolve():
                        shutil.copy2(path, target)
                    self.database.set_setting("background", str(target))
            elif chosen == clear_bg:
                self.database.set_setting("background", "")
            elif chosen == startup:
                set_startup_enabled(startup.isChecked())
            elif chosen == backup:
                self.statusBar().showMessage("备份已保存：" + str(self.backups.create_backup()), 8000)
            elif chosen == export:
                path, _ = QFileDialog.getSaveFileName(self, "导出备份", "DeskNest-backup.db", "DeskNest 备份 (*.db)")
                if path:
                    self.database.backup_to(path)
                    self.statusBar().showMessage("备份已导出", 5000)
            elif chosen == restore:
                dialog = RestoreDialog(self.backups.list_backups(), self)
                if dialog.exec() == dialog.DialogCode.Accepted:
                    self._restore(dialog.selected_backup())
            elif chosen == import_backup:
                path, _ = QFileDialog.getOpenFileName(self, "选择备份", "", "DeskNest 备份 (*.db)")
                if path:
                    dialog = RestoreDialog([Path(path)], self)
                    if dialog.exec() == dialog.DialogCode.Accepted:
                        self._restore(Path(path))
            elif chosen == quit_action:
                self._quit()
                return
            self._apply_theme()
        except Exception as error:
            self._show_error("设置失败", error)

    def _restore(self, path):
        self.backups.restore(path)
        self.current_category_id = None
        self._icon_cache.clear()
        self.search.clear()
        self.refresh()
        self._apply_theme()
        self.statusBar().showMessage("已恢复，恢复前的状态已自动保存在备份列表", 8000)

    def _desktop_changed(self):
        self._icon_cache.clear()
        self.statusBar().showMessage("桌面内容有变化，点击「扫描桌面」查看新增项目")

    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self):
        self._allow_close = True
        self.close()

    def closeEvent(self, event: QCloseEvent):
        if not self._allow_close and self.tray:
            self.hide()
            event.ignore()
            return
        if self._scan_worker and self._scan_worker.isRunning():
            self.statusBar().showMessage("请等待扫描完成后退出")
            self._allow_close = False
            event.ignore()
            return
        if self.hotkey:
            self.hotkey.close()
        if self.tray:
            self.tray.hide()
        self.database.close()
        event.accept()
        QApplication.instance().quit()

    def _show_error(self, title, error):
        logging.error("%s: %s", title, error, exc_info=True)
        detail = "名称已存在，请使用其他名称。" if "UNIQUE constraint" in str(error) else str(error)
        QMessageBox.warning(self, title, detail)
