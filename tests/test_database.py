from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from desknest.models import DesktopItem
from desknest.storage.database import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")
        self.database.initialize()

    def tearDown(self) -> None:
        self.database.close()
        self.temp_dir.cleanup()

    def test_default_categories_and_item_round_trip(self) -> None:
        categories = self.database.categories()
        self.assertEqual(
            [category.name for category in categories],
            ["\u5e38\u7528", "\u529e\u516c", "\u6e38\u620f", "\u8bbe\u8ba1", "\u5de5\u5177", "\u6587\u4ef6"],
        )
        item = self.database.upsert_item(
            DesktopItem(None, "\u8bb0\u4e8b\u672c", r"C:\Windows\notepad.exe", "file", categories[0].id)
        )
        self.assertEqual(self.database.items(categories[0].id)[0].name, "\u8bb0\u4e8b\u672c")
        self.database.update_item_flags(item.id, favorite=True, pinned=True)
        loaded = self.database.item(item.id)
        self.assertIsNotNone(loaded)
        self.assertTrue(loaded.is_favorite)
        self.assertTrue(loaded.is_pinned)

    def test_delete_category_moves_items(self) -> None:
        categories = self.database.categories()
        self.database.upsert_item(DesktopItem(None, "\u6587\u4ef6", "C:/file.txt", "file", categories[1].id))
        self.database.delete_category(categories[1].id)
        moved = self.database.items(categories[0].id)
        self.assertEqual(len(moved), 1)
        self.assertEqual(moved[0].name, "\u6587\u4ef6")
        self.assertEqual(len(self.database.categories()), 5)


if __name__ == "__main__":
    unittest.main()
