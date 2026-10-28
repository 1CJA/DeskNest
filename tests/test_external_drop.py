"""Exercise Qt drop dispatch, destinations, undo and preservation of source files."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt, QCoreApplication, QEvent, QMimeData, QPoint, QPointF, QUrl
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from desknest.services.scanner import DesktopScanner
from desknest.storage.database import Database
from desknest.ui.main_window import MainWindow
from desknest.ui.widgets import ITEM_MIME, CATEGORY_MIME, ROLE


class ExternalDropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = Database(self.root / "test.db")
        self.db.initialize()
        self.existing = self.make_file("已有项目.txt")
        self.item = self.db.upsert_item(DesktopScanner.from_path(self.existing))
        self.window = MainWindow(self.db, integrations=False)
        self.window.show()
        QTest.qWait(20)

    def tearDown(self):
        self.window._allow_close = True
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.temp.cleanup()

    def make_file(self, name):
        path = self.root / name
        path.write_text("original content", encoding="utf-8")
        return path

    def history_count(self):
        return self.db.connection.execute("SELECT COUNT(*) FROM history").fetchone()[0]

    def category_point(self, category_id):
        categories = self.window.categories
        row = next(categories.item(i) for i in range(categories.count())
                   if categories.item(i).data(ROLE) == category_id)
        return categories.visualItemRect(row).center()

    def select_category(self, category_id):
        categories = self.window.categories
        for index in range(categories.count()):
            if categories.item(index).data(ROLE) == category_id:
                categories.setCurrentRow(index)
                self.app.processEvents()
                return
        self.fail("category missing")

    def send_drop(self, receiver, paths=(), *, point=None, mime=None,
                  actions=Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                  modifiers=Qt.KeyboardModifier.ShiftModifier,
                  expected=Qt.DropAction.CopyAction):
        if mime is None:
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
        point = point if point is not None else receiver.rect().center()
        enter = QDragEnterEvent(point, actions, mime, Qt.MouseButton.LeftButton, modifiers)
        self.app.sendEvent(receiver, enter)
        self.assertEqual(enter.isAccepted(), expected is not None)
        if expected is None:
            return
        self.assertEqual(enter.dropAction(), expected)
        move = QDragMoveEvent(point, actions, mime, Qt.MouseButton.LeftButton, modifiers)
        self.app.sendEvent(receiver, move)
        self.assertTrue(move.isAccepted())
        self.assertEqual(move.dropAction(), expected)
        drop = QDropEvent(QPointF(point), actions, mime, Qt.MouseButton.LeftButton, modifiers)
        self.app.sendEvent(receiver, drop)
        self.assertTrue(drop.isAccepted())
        self.assertEqual(drop.dropAction(), expected)
        self.app.processEvents()

    def test_grid_batch_keeps_sources_launches_original_and_undoes_together(self):
        paths = [self.make_file(name) for name in ("中文 快捷方式.lnk", "网页.url", "会议 # 记录.txt")]
        folder = self.root / "资料 文件夹"
        folder.mkdir()
        child = folder / "内容.txt"
        child.write_text("keep me", encoding="utf-8")
        paths.append(folder)
        before = self.history_count()
        with patch.object(self.window.launcher, "launch") as launch:
            self.send_drop(self.window.item_list.viewport(), paths)
            launch.assert_not_called()
        items = {Path(i.path): i for i in self.db.items()}
        self.assertEqual(len(items), 5)
        self.assertEqual([items[p].item_type for p in paths], ["shortcut", "web", "file", "folder"])
        for path in paths:
            self.assertEqual(items[path].source_path, str(path))
        self.assertEqual(self.history_count(), before + 1)
        self.window.search.setText("中文 快捷方式")
        grid = self.window.item_list
        self.assertEqual(grid.count(), 1)
        with patch.object(self.window.launcher, "launch") as launch:
            QTest.mouseClick(grid.viewport(), Qt.MouseButton.LeftButton,
                             pos=grid.visualItemRect(grid.item(0)).center())
            self.assertEqual(launch.call_args.args[0].path, str(paths[0]))
        self.window._undo()
        self.assertEqual([i.path for i in self.db.items()], [str(self.existing)])
        for path in paths[:-1]:
            self.assertEqual(path.read_text(encoding="utf-8"), "original content")
        self.assertEqual(child.read_text(encoding="utf-8"), "keep me")

    def test_empty_category_receives_external_files(self):
        target = self.db.categories()[2].id
        self.select_category(target)
        self.assertTrue(self.window.empty.isVisible())
        self.assertFalse(self.window.item_list.isVisible())
        path = self.make_file("游戏.lnk")
        self.send_drop(self.window.empty, [path])
        self.assertEqual([i.path for i in self.db.items(target)], [str(path)])
        self.assertTrue(self.window.item_list.isVisible())

    def test_empty_library_uses_first_category(self):
        self.db.delete_item(self.item.id)
        self.window.refresh()
        self.send_drop(self.window.empty, [self.existing])
        self.assertEqual(self.db.items()[0].category_id, self.db.categories()[0].id)

    def test_sidebar_drop_uses_destination_including_all_items(self):
        for target in (self.db.categories()[3].id, 0):
            with self.subTest(target=target):
                path = self.make_file(f"分区 {target}.txt")
                self.send_drop(self.window.categories.viewport(), [path], point=self.category_point(target))
                item = next(i for i in self.db.items() if i.path == str(path))
                expected = target or self.db.categories()[0].id
                self.assertEqual(item.category_id, expected)
                self.assertEqual(self.window.current_category_id, expected)

    def test_duplicates_preserve_category_flags_and_do_not_add_undo_steps(self):
        self.db.update_item_flags(self.item.id, favorite=True, pinned=True)
        self.window.refresh()
        before = self.history_count()
        target = self.db.categories()[2].id
        self.send_drop(self.window.categories.viewport(), [self.existing, self.existing],
                       point=self.category_point(target))
        self.assertEqual(len(self.db.items()), 1)
        item = self.db.item(self.item.id)
        self.assertEqual(item.category_id, self.item.category_id)
        self.assertTrue(item.is_favorite)
        self.assertTrue(item.is_pinned)
        self.assertEqual(self.history_count(), before)
        self.assertIn("2 个已存在", self.window.statusBar().currentMessage())
        new = self.make_file("新项目.txt")
        self.send_drop(self.window.item_list.viewport(), [new, new, self.existing])
        self.assertEqual(len(self.db.items()), 2)
        self.assertEqual(self.history_count(), before + 1)

    def test_search_drop_clears_filter_and_uses_selected_category(self):
        target = self.db.categories()[1].id
        self.select_category(target)
        for query in ("已有项目", "不存在的搜索词"):
            with self.subTest(query=query):
                self.window.search.setText(query)
                receiver = self.window.empty if self.window.empty.isVisible() else self.window.item_list.viewport()
                path = self.make_file(f"{query}导入.txt")
                self.send_drop(receiver, [path])
                self.assertEqual(self.window.search.text(), "")
                self.assertEqual(self.window.current_category_id, target)
                self.assertIn(str(path), [i.path for i in self.db.items(target)])

    def test_background_accepts_files(self):
        path = self.make_file("背景留白.txt")
        self.send_drop(self.window.root, [path], point=QPoint(2, 2))
        self.assertIn(str(path), [i.path for i in self.db.items()])

    def test_nonlocal_urls_virtual_objects_and_move_only_drops_are_rejected(self):
        web = QMimeData()
        web.setUrls([QUrl("https://example.com/")])
        virtual = QMimeData()
        virtual.setData('application/x-qt-windows-mime;value="Shell IDList Array"', b"virtual")
        for receiver in (self.window.item_list.viewport(), self.window.empty, self.window.root,
                         self.window.categories.viewport()):
            for mime in (web, virtual):
                with self.subTest(receiver=type(receiver).__name__, mime=mime.formats()):
                    self.send_drop(receiver, mime=mime, expected=None)
        self.send_drop(self.window.item_list.viewport(), [self.existing],
                       actions=Qt.DropAction.MoveAction, expected=None)
        self.assertEqual(len(self.db.items()), 1)
        self.assertTrue(self.existing.exists())

    def test_missing_path_reports_failure_and_imports_valid_part(self):
        new = self.make_file("正常文件.txt")
        before = self.history_count()
        with patch("desknest.ui.main_window.QMessageBox.warning") as warning:
            self.send_drop(self.window.item_list.viewport(), [self.root / "missing.lnk", new])
            warning.assert_called_once()
            self.assertIn("missing.lnk", warning.call_args.args[2])
        self.assertEqual(len(self.db.items()), 2)
        self.assertIn("1 个无法读取", self.window.statusBar().currentMessage())
        self.assertEqual(self.history_count(), before + 1)
        self.window._undo()
        self.assertEqual(len(self.db.items()), 1)
        self.assertTrue(new.exists())

    def test_database_failure_does_not_change_sources_or_report_success(self):
        new = self.make_file("保留文件.txt")
        before = self.history_count()
        with patch.object(self.db, "add_items", side_effect=OSError("disk full")), \
                patch.object(self.window, "_show_error") as error:
            self.send_drop(self.window.item_list.viewport(), [new])
            error.assert_called_once()
        self.assertEqual(len(self.db.items()), 1)
        self.assertEqual(self.history_count(), before)
        self.assertEqual(new.read_text(encoding="utf-8"), "original content")

    def test_internal_card_and_category_reordering_still_use_move(self):
        new = self.make_file("第二个.txt")
        second = self.db.upsert_item(DesktopScanner.from_path(new))
        self.window.refresh()
        mime = QMimeData()
        mime.setData(ITEM_MIME, str(second.id).encode())
        grid = self.window.item_list
        self.send_drop(grid.viewport(), mime=mime, point=grid.visualItemRect(grid.item(0)).center(),
                       actions=Qt.DropAction.MoveAction, expected=Qt.DropAction.MoveAction)
        self.assertEqual(self.db.items()[0].id, second.id)
        category_ids = [c.id for c in self.db.categories()]
        mime = QMimeData()
        mime.setData(CATEGORY_MIME, str(category_ids[-1]).encode())
        self.send_drop(self.window.categories.viewport(), mime=mime,
                       point=self.category_point(category_ids[0]), actions=Qt.DropAction.MoveAction,
                       expected=Qt.DropAction.MoveAction)
        self.assertEqual(self.db.categories()[0].id, category_ids[-1])
