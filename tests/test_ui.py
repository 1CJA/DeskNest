import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt, QCoreApplication, QEvent, QMimeData, QPoint, QPointF
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from desknest.models import DesktopItem
from desknest.storage.database import Database
from desknest.ui.main_window import MainWindow
from desknest.ui.dialogs import ScanDialog
from desknest.ui.widgets import ITEM_MIME

class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name)/"test.db")
        self.db.initialize()
        self.file = Path(self.temp.name)/"hello.txt"
        self.file.write_text("test")
        self.item = self.db.upsert_item(DesktopItem(None,"Hello",str(self.file),"file"))
        self.window = MainWindow(self.db, integrations=False)
        self.window.show()
        QTest.qWait(30)

    def tearDown(self):
        self.window._allow_close = True
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.temp.cleanup()

    def test_card_launch_search_and_scan_selection(self):
        grid = self.window.item_list
        with patch.object(self.window.launcher, "launch") as launch:
            QTest.mouseClick(grid.viewport(), Qt.MouseButton.LeftButton,
                             pos=grid.visualItemRect(grid.item(0)).center())
            launch.assert_called_once()
        self.window.search.setText("missing")
        self.assertEqual(grid.count(),0)
        self.assertTrue(self.window.empty.isVisible())
        self.window.search.setText("hello")
        self.assertEqual(grid.count(),1)
        dialog = ScanDialog([self.item],self.db.categories())
        self.assertEqual(dialog.selected_items(), [])
        dialog._select(Qt.CheckState.Checked)
        self.assertEqual(len(dialog.selected_items()),1)
        dialog.close()

    def test_category_drop_accepts_mime_and_moves_item(self):
        categories = self.window.categories
        target = self.db.categories()[1].id
        row = next(categories.item(i) for i in range(categories.count())
                   if categories.item(i).data(Qt.ItemDataRole.UserRole) == target)
        point = categories.visualItemRect(row).center()
        mime = QMimeData()
        mime.setData(ITEM_MIME,str(self.item.id).encode())
        enter = QDragEnterEvent(point, Qt.DropAction.MoveAction,mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        categories.dragEnterEvent(enter)
        self.assertTrue(enter.isAccepted())
        drop = QDropEvent(QPointF(point),Qt.DropAction.MoveAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        categories.dropEvent(drop)
        self.app.processEvents()
        self.assertEqual(self.db.item(self.item.id).category_id,target)
        self.window._undo()
        self.assertEqual(self.db.item(self.item.id).category_id,self.item.category_id)
