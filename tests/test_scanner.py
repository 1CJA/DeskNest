from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desknest.services.scanner import DesktopScanner


class ScannerTests(unittest.TestCase):
    def test_scans_files_and_folders_without_modifying_them(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            desktop = Path(temporary)
            (desktop / "\u5de5\u5177.txt").write_text("DeskNest", encoding="utf-8")
            (desktop / "\u6e38\u620f").mkdir()
            scanner = DesktopScanner()
            with patch.object(scanner, "desktop_paths", return_value=[desktop]):
                items = scanner.scan()
            self.assertEqual({item.name for item in items}, {"\u5de5\u5177.txt", "\u6e38\u620f"})
            self.assertTrue((desktop / "\u5de5\u5177.txt").exists())
            self.assertTrue((desktop / "\u6e38\u620f").exists())


if __name__ == "__main__":
    unittest.main()

