from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sqlite3
from contextlib import closing
import os

from desknest.models import DesktopItem
from desknest.storage.database import Database
from desknest.services.scanner import DesktopScanner
from desknest.services.launcher import Launcher
from desknest.services.backup import BackupService
from desknest.windows.startup import startup_command

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.desktop = self.root / "Desktop"
        self.desktop.mkdir()
        self.file = self.desktop / "笔记.txt"
        self.file.write_text("do not lose this", encoding="utf-8")
        self.db = Database(self.root / "data" / "test.db")
        self.db.initialize()

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_scan_select_category_search_launch_backup_restore_undo(self):
        (self.desktop / "工作").mkdir()
        (self.desktop / "desktop.ini").write_text("hidden")
        scanner = DesktopScanner()
        with patch.object(scanner, "desktop_paths", return_value=[self.desktop]):
            found = scanner.scan()
        self.assertEqual(len(found), 2)
        selected = next(i for i in found if i.name == "笔记.txt")
        category = self.db.create_category("项目")
        self.db.add_items([selected], category.id)
        self.assertEqual(len(self.db.items()), 1)
        item = self.db.items(query="笔记")[0]
        with patch("os.startfile") as launch:
            Launcher().launch(item)
            launch.assert_called_once_with(str(self.file))
        backup = BackupService(self.db).create_backup()
        other = self.db.categories()[0]
        self.db.update_item_category(item.id, other.id)
        self.db.undo()
        self.assertEqual(self.db.item(item.id).category_id, category.id)
        self.db.delete_item(item.id)
        self.assertEqual(self.db.items(), [])
        self.db.restore_from(backup)
        self.assertEqual(self.db.items()[0].name, "笔记.txt")
        self.assertEqual(self.file.read_text(encoding="utf-8"), "do not lose this")
        self.assertTrue(list((self.db.path.parent/"backups").glob("before-restore-*.db")))

    def test_bad_backup_never_changes_current_data(self):
        self.db.upsert_item(DesktopItem(None,"笔记",str(self.file),"file"))
        invalid = self.root / "broken.db"
        invalid.write_bytes(b"not a database")
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.restore_from(invalid)
        self.assertEqual(len(self.db.items()), 1)
        with closing(sqlite3.connect(self.root/"empty.db")) as c:
            c.execute("CREATE TABLE something (id)")
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.restore_from(self.root/"empty.db")
        self.assertEqual(len(self.db.items()), 1)

    def test_replace_failure_keeps_data_and_reopens_connection(self):
        backup = BackupService(self.db).create_backup()
        self.db.create_category("保留")
        actual_replace = os.replace
        def failing(src, dst):
            if Path(dst) == self.db.path:
                raise PermissionError("simulated locked destination")
            return actual_replace(src, dst)
        with patch("desknest.storage.database.os.replace", side_effect=failing):
            with self.assertRaises(PermissionError):
                self.db.restore_from(backup)
        self.assertIn("保留", [c.name for c in self.db.categories()])

    def test_failed_mutation_rolls_back_history_and_data(self):
        before = self.db.undo_label()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.create_category(self.db.categories()[0].name)
        self.assertEqual(self.db.undo_label(), before)
        self.assertEqual(len(self.db.categories()), 6)

    def test_duplicate_import_preserves_flags_and_category(self):
        item = self.db.upsert_item(DesktopItem(None,"笔记",str(self.file),"file"))
        self.db.update_item_flags(item.id, favorite=True, pinned=True)
        self.db.add_items([item], self.db.categories()[1].id)
        loaded = self.db.item(item.id)
        self.assertEqual(loaded.category_id, item.category_id)
        self.assertTrue(loaded.is_favorite and loaded.is_pinned)

    def test_missing_shortcut_does_not_fall_back_to_target(self):
        item = DesktopItem(None, "missing", str(self.desktop/"missing.lnk"),"shortcut",shortcut_target="notepad.exe")
        with patch("os.startfile") as launch:
            with self.assertRaises(FileNotFoundError):
                Launcher().launch(item)
            launch.assert_not_called()

    def test_real_shortcut_preserves_arguments_and_working_directory(self):
        import win32com.client
        shortcut = self.desktop / "测试.lnk"
        link = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(shortcut))
        link.TargetPath = str(Path(os.environ["WINDIR"])/"System32"/"cmd.exe")
        link.Arguments = '/c exit 0'
        link.WorkingDirectory = str(self.desktop)
        link.Save()
        item = DesktopScanner.from_path(shortcut)
        with patch("os.startfile") as launch:
            Launcher().launch(item)
            launch.assert_called_once_with(str(shortcut))

    def test_undo_survives_restart_and_delete_category(self):
        category = self.db.create_category("工作")
        item = self.db.upsert_item(DesktopItem(None,"笔记",str(self.file),"file",category.id))
        self.db.delete_category(category.id)
        self.db.close()
        self.db.initialize()
        self.db.undo()
        self.assertEqual(self.db.item(item.id).category_id, category.id)

    def test_search_literal_percent_unicode_and_order(self):
        a = self.db.upsert_item(DesktopItem(None,"100% 完成",str(self.file),"file"))
        b = self.db.upsert_item(DesktopItem(None,"ABC",str(self.desktop/"other.txt"),"file"))
        self.assertEqual([i.id for i in self.db.items(query="%")],[a.id])
        self.assertEqual([i.id for i in self.db.items(query="abc")],[b.id])
        self.db.reorder_items([b.id,a.id])
        self.assertEqual([i.id for i in self.db.items()],[b.id,a.id])
        self.db.undo()
        self.assertEqual([i.id for i in self.db.items()],[a.id,b.id])

    def test_backup_names_unique_and_startup_includes_entrypoint(self):
        service = BackupService(self.db)
        self.assertNotEqual(service.create_backup(), service.create_backup())
        self.assertIn("main.py", startup_command())
        self.assertIn("--minimized", startup_command())
