from pathlib import Path
from PySide6.QtCore import Qt, QFileInfo
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QFileIconProvider)

TYPES = {"shortcut":"快捷方式", "folder":"文件夹", "file":"文件", "web":"网页快捷方式"}

class ScanDialog(QDialog):
    def __init__(self, items, categories, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择收纳")
        self.resize(720, 540)
        layout = QVBoxLayout(self)
        label = QLabel(f"发现 {len(items)} 个未收纳项目。选择要添加的内容，原文件会保留在桌面。")
        label.setWordWrap(True)
        layout.addWidget(label)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("收纳到"))
        self.category = QComboBox()
        for category in categories:
            self.category.addItem(category.name, category.id)
        controls.addWidget(self.category)
        controls.addStretch()
        for text, state in (("全选", Qt.CheckState.Checked), ("清空", Qt.CheckState.Unchecked)):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False,s=state: self._select(s))
            controls.addWidget(button)
        layout.addLayout(controls)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        icons = QFileIconProvider()
        for item in items:
            row = QListWidgetItem(f"{item.name} · {TYPES.get(item.item_type, '文件')}")
            row.setData(Qt.ItemDataRole.UserRole, item)
            row.setToolTip(item.path)
            row.setIcon(icons.icon(QFileInfo(item.path)))
            row.setCheckState(Qt.CheckState.Checked if item.item_type in ("shortcut", "web") else Qt.CheckState.Unchecked)
            self.list_widget.addItem(row)
        layout.addWidget(self.list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("收纳所选")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _select(self, state):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(state)

    def selected_items(self):
        return [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list_widget.count())
                if self.list_widget.item(i).checkState() == Qt.CheckState.Checked]

    def selected_category_id(self):
        return self.category.currentData()

    def _accept(self):
        if not self.selected_items():
            QMessageBox.information(self, "选择项目", "请至少选择一个项目。")
            return
        self.accept()

class RestoreDialog(QDialog):
    def __init__(self, backups, parent=None):
        super().__init__(parent)
        self.setWindowTitle("恢复应用布局")
        self.resize(620, 420)
        layout = QVBoxLayout(self)
        label = QLabel("恢复分区、项目引用、排序和设置。恢复前会自动保存当前状态。\n备份不包含原始文件内容或 Windows 桌面图标坐标。")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.list_widget = QListWidget()
        for path in backups:
            row = QListWidgetItem(path.name)
            row.setData(Qt.ItemDataRole.UserRole, str(path))
            self.list_widget.addItem(row)
        if backups:
            self.list_widget.setCurrentRow(0)
        layout.addWidget(self.list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("恢复")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_backup(self):
        row = self.list_widget.currentItem()
        return Path(row.data(Qt.ItemDataRole.UserRole)) if row else None

    def _accept(self):
        if self.selected_backup() and QMessageBox.question(self, "确认恢复", "使用选中的备份恢复 DeskNest？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.accept()
