from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    sort_order: int


@dataclass(frozen=True)
class DesktopItem:
    id: int | None
    name: str
    path: str
    item_type: str
    category_id: int | None = None
    is_favorite: bool = False
    is_pinned: bool = False
    sort_order: int = 0
    shortcut_target: Optional[str] = None
    source_path: Optional[str] = None

