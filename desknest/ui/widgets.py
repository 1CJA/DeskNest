from PySide6.QtCore import Qt, Signal, QSize, QMimeData, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QListWidget, QStyledItemDelegate, QStyle, QWidget

ITEM_MIME = "application/x-desknest-item"
CATEGORY_MIME = "application/x-desknest-category"
ROLE = Qt.ItemDataRole.UserRole


def accept_local_files(event):
    """Accept references as Copy, so Explorer must never remove the originals."""
    mime = event.mimeData()
    urls = mime.urls()
    if (mime.hasFormat(ITEM_MIME) or mime.hasFormat(CATEGORY_MIME)
            or not urls or not all(url.isLocalFile() for url in urls)
            or not event.possibleActions() & Qt.DropAction.CopyAction):
        event.ignore()
        return []
    paths = [url.toLocalFile() for url in urls]
    if not all(paths):
        event.ignore()
        return []
    event.setDropAction(Qt.DropAction.CopyAction)
    event.accept()
    return paths


class FileDropLabel(QLabel):
    filesDropped = Signal(list)

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        accept_local_files(event)

    def dragMoveEvent(self, event):
        accept_local_files(event)

    def dropEvent(self, event):
        paths = accept_local_files(event)
        if paths:
            self.filesDropped.emit(paths)

class CategoryListWidget(QListWidget):
    itemDropped = Signal(int, int)
    categoryDropped = Signal(int, int)
    filesDropped = Signal(list, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("categories")
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def mimeData(self, items):
        mime = QMimeData()
        if items and items[0].data(ROLE):
            mime.setData(CATEGORY_MIME, str(items[0].data(ROLE)).encode())
        return mime

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(ITEM_MIME) or event.mimeData().hasFormat(CATEGORY_MIME):
            event.acceptProposedAction()
        else:
            accept_local_files(event)

    def dragMoveEvent(self, event):
        target = self.itemAt(event.position().toPoint())
        if not target:
            event.ignore()
        elif not (event.mimeData().hasFormat(ITEM_MIME) or event.mimeData().hasFormat(CATEGORY_MIME)):
            accept_local_files(event)
        elif target.data(ROLE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        target = self.itemAt(event.position().toPoint())
        if not target:
            event.ignore()
            return
        mime = event.mimeData()
        if not (mime.hasFormat(ITEM_MIME) or mime.hasFormat(CATEGORY_MIME)):
            paths = accept_local_files(event)
            if paths:
                self.filesDropped.emit(paths, int(target.data(ROLE)))
            return
        if not target.data(ROLE):
            event.ignore()
            return
        try:
            if mime.hasFormat(ITEM_MIME):
                self.itemDropped.emit(int(bytes(mime.data(ITEM_MIME))), int(target.data(ROLE)))
            elif mime.hasFormat(CATEGORY_MIME):
                self.categoryDropped.emit(int(bytes(mime.data(CATEGORY_MIME))), int(target.data(ROLE)))
            else:
                event.ignore()
                return
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        except ValueError:
            event.ignore()

class ItemGrid(QListWidget):
    reorderRequested = Signal(int, int)
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("items")
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Snap)
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setSpacing(8)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setWordWrap(False)
        self.setMouseTracking(True)
        self.setItemDelegate(CardDelegate(self))
        self.set_icon_size(48)

    def set_icon_size(self, pixels):
        self.setIconSize(QSize(pixels, pixels))
        self.setGridSize(QSize(188, pixels + 92))

    def mimeData(self, items):
        mime = QMimeData()
        if items:
            mime.setData(ITEM_MIME, str(items[0].data(ROLE)).encode())
        return mime

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(ITEM_MIME):
            event.acceptProposedAction()
        else:
            accept_local_files(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(ITEM_MIME):
            event.acceptProposedAction()
        else:
            accept_local_files(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(ITEM_MIME):
            paths = accept_local_files(event)
            if paths:
                self.filesDropped.emit(paths)
            return
        try:
            source = int(bytes(event.mimeData().data(ITEM_MIME)))
            target = self.itemAt(event.position().toPoint())
            self.reorderRequested.emit(source, int(target.data(ROLE)) if target else 0)
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        except ValueError:
            event.ignore()

class CardDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return self.parent().gridSize()

    def paint(self, painter, option, index):
        dark = bool(self.parent().property("dark"))
        rect = option.rect.adjusted(4, 4, -4, -4)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#252c3b" if dark else "#ffffff"))
        painter.setPen(QPen(QColor("#7083ff" if selected or hover else "#343e52" if dark else "#e1e6ef"), 1))
        painter.drawRoundedRect(rect, 13, 13)
        size = self.parent().iconSize().width()
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        icon.paint(painter, QRect(rect.x()+16, rect.y()+14, size, size))
        pinned, favorite, kind = index.data(ROLE+1)
        painter.setPen(QColor("#9dafff" if dark else "#536dfe"))
        badge = ("置顶 " if pinned else "") + ("★" if favorite else "")
        painter.drawText(rect.adjusted(70,12,-12,-12), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, badge)
        font = option.font
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#f0f3fa" if dark else "#222d44"))
        text = painter.fontMetrics().elidedText(index.data(), Qt.TextElideMode.ElideRight, rect.width()-28)
        painter.drawText(QRect(rect.x()+14, rect.y()+size+23, rect.width()-28, 24),
                         Qt.AlignmentFlag.AlignVCenter, text)
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor("#95a0b4" if dark else "#7c879b"))
        painter.drawText(QRect(rect.x()+14, rect.y()+size+49, rect.width()-28, 22),
                         Qt.AlignmentFlag.AlignVCenter, kind)
        painter.restore()

class Background(QWidget):
    filesDropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.pixmap = QPixmap()
        self.dark = False

    def dragEnterEvent(self, event):
        accept_local_files(event)

    def dragMoveEvent(self, event):
        accept_local_files(event)

    def dropEvent(self, event):
        paths = accept_local_files(event)
        if paths:
            self.filesDropped.emit(paths)

    def set_background(self, path, dark):
        self.pixmap = QPixmap(path) if path else QPixmap()
        self.dark = dark
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.pixmap.isNull():
            scaled = self.pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                        Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((self.width()-scaled.width())//2, (self.height()-scaled.height())//2, scaled)
            painter.fillRect(self.rect(), QColor(16,21,32,205) if self.dark else QColor(246,248,252,210))
