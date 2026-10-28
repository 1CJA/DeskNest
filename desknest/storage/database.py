from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from desknest.config import DATABASE_PATH
from desknest.models import Category, DesktopItem

DEFAULT_CATEGORIES = ('常用', '办公', '游戏', '设计', '工具', '文件')
TABLES = ('categories', 'items', 'settings')


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Database:
    """Every library edit and its undo snapshot commit together."""

    def __init__(self, path: Path | str = DATABASE_PATH):
        self.path = Path(path)
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.path, timeout=10)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute('PRAGMA foreign_keys = ON')
            self._connection.execute('PRAGMA synchronous = FULL')
        return self._connection

    def initialize(self):
        c = self.connection
        if c.execute('PRAGMA user_version').fetchone()[0] > 1:
            raise ValueError('数据来自更新版本的 DeskNest，请升级软件后打开。')
        c.executescript('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE COLLATE NOCASE, item_type TEXT NOT NULL,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                is_favorite INTEGER NOT NULL DEFAULT 0, is_pinned INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0, shortcut_target TEXT, source_path TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL,
                snapshot TEXT NOT NULL, created_at TEXT NOT NULL);
            PRAGMA user_version = 1;
        ''')
        with c:
            if not c.execute('SELECT 1 FROM categories LIMIT 1').fetchone():
                c.executemany('INSERT INTO categories(name,sort_order,created_at) VALUES(?,?,?)',
                              [(name, i, utc_now()) for i, name in enumerate(DEFAULT_CATEGORIES)])

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @contextmanager
    def _edit(self, label):
        c = self.connection
        with c:
            c.execute('BEGIN IMMEDIATE')
            snapshot = {t: [dict(r) for r in c.execute(f'SELECT * FROM {t}')] for t in TABLES}
            c.execute('INSERT INTO history(label,snapshot,created_at) VALUES(?,?,?)',
                      (label, json.dumps(snapshot, ensure_ascii=False), utc_now()))
            yield c
            c.execute('DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 30)')

    def undo_label(self):
        row = self.connection.execute('SELECT label FROM history ORDER BY id DESC LIMIT 1').fetchone()
        return row[0] if row else None

    def undo(self):
        c = self.connection
        with c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM history ORDER BY id DESC LIMIT 1').fetchone()
            if row is None:
                raise ValueError('没有可撤销的操作。')
            data = json.loads(row['snapshot'])
            for table in ('items', 'categories'):
                c.execute(f'DELETE FROM {table}')
            for table in ('categories', 'items'):
                allowed = {r[1] for r in c.execute(f'PRAGMA table_info({table})')}
                for record in data[table]:
                    columns = list(record)
                    if set(columns) != allowed:
                        raise ValueError('撤销记录的格式不正确。')
                    c.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                              list(record.values()))
            c.execute('DELETE FROM history WHERE id=?', (row['id'],))
        return row['label']

    def categories(self):
        return [Category(**dict(r)) for r in self.connection.execute(
            'SELECT id,name,sort_order FROM categories ORDER BY sort_order,id')]

    def category(self, category_id):
        return next((c for c in self.categories() if c.id == category_id), None)

    @staticmethod
    def _name(name):
        name = name.strip()
        if not name or len(name) > 50:
            raise ValueError('分区名称需要为 1～50 个字符。')
        return name

    def create_category(self, name):
        name = self._name(name)
        with self._edit('新建分区') as c:
            order = c.execute('SELECT COALESCE(MAX(sort_order),-1)+1 FROM categories').fetchone()[0]
            row = c.execute('INSERT INTO categories(name,sort_order,created_at) VALUES(?,?,?)', (name, order, utc_now()))
            result = Category(row.lastrowid, name, order)
        return result

    def rename_category(self, category_id, name):
        name = self._name(name)
        with self._edit('重命名分区') as c:
            c.execute('UPDATE categories SET name=? WHERE id=?', (name, category_id))

    def delete_category(self, category_id):
        categories = self.categories()
        if len(categories) <= 1:
            raise ValueError('至少需要保留一个分区。')
        if self.category(category_id) is None:
            raise ValueError('分区已不存在。')
        fallback = next(cat.id for cat in categories if cat.id != category_id)
        with self._edit('删除分区') as c:
            c.execute('UPDATE items SET category_id=?,updated_at=? WHERE category_id=?', (fallback, utc_now(), category_id))
            c.execute('DELETE FROM categories WHERE id=?', (category_id,))

    def reorder_categories(self, ordered_ids):
        if sorted(ordered_ids) != sorted(c.id for c in self.categories()):
            raise ValueError('分区列表已变化，请重试。')
        with self._edit('分区排序') as c:
            c.executemany('UPDATE categories SET sort_order=? WHERE id=?', enumerate(ordered_ids))

    def items(self, category_id=None, query=''):
        rows = self.connection.execute('SELECT * FROM items ORDER BY is_pinned DESC,sort_order,id')
        items = [self._item(r) for r in rows]
        if category_id is not None:
            items = [i for i in items if i.category_id == category_id]
        words = query.strip().casefold().split()
        return [i for i in items if all(w in (i.name+' '+i.path).casefold() for w in words)]

    def item(self, item_id):
        row = self.connection.execute('SELECT * FROM items WHERE id=?', (item_id,)).fetchone()
        return self._item(row) if row else None

    def add_items(self, items, category_id):
        if self.category(category_id) is None:
            raise ValueError('请选择有效分区。')
        known = {os.path.normcase(i.path) for i in self.items()}
        new = []
        for item in items:
            key = os.path.normcase(item.path)
            if key not in known:
                known.add(key)
                new.append(item)
        if not new:
            return 0
        with self._edit('收纳项目') as c:
            order = c.execute('SELECT COALESCE(MAX(sort_order),-1)+1 FROM items').fetchone()[0]
            for index, item in enumerate(new):
                c.execute('''INSERT INTO items(name,path,item_type,category_id,is_favorite,is_pinned,
                             sort_order,shortcut_target,source_path,created_at,updated_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                          (item.name, item.path, item.item_type, category_id, int(item.is_favorite),
                           int(item.is_pinned), order+index, item.shortcut_target, item.source_path or item.path,
                           utc_now(), utc_now()))
        return len(new)

    def upsert_item(self, item):
        self.add_items([item], item.category_id or self.categories()[0].id)
        return next(i for i in self.items() if os.path.normcase(i.path) == os.path.normcase(item.path))

    def update_item_category(self, item_id, category_id):
        if self.category(category_id) is None:
            raise ValueError('分区已不存在。')
        with self._edit('移动到分区') as c:
            c.execute('UPDATE items SET category_id=?,updated_at=? WHERE id=?', (category_id, utc_now(), item_id))

    def reorder_items(self, ordered_ids):
        if len(set(ordered_ids)) != len(ordered_ids):
            raise ValueError('项目顺序无效。')
        with self._edit('项目排序') as c:
            c.executemany('UPDATE items SET sort_order=? WHERE id=?', enumerate(ordered_ids))

    def update_item_flags(self, item_id, *, favorite=None, pinned=None):
        with self._edit('收藏 / 置顶') as c:
            if favorite is not None:
                c.execute('UPDATE items SET is_favorite=? WHERE id=?', (int(favorite), item_id))
            if pinned is not None:
                c.execute('UPDATE items SET is_pinned=? WHERE id=?', (int(pinned), item_id))

    def delete_item(self, item_id):
        with self._edit('移除引用') as c:
            c.execute('DELETE FROM items WHERE id=?', (item_id,))

    def set_setting(self, key, value):
        with self.connection as c:
            c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))

    def setting(self, key, default=None):
        row = self.connection.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return row[0] if row else default

    def backup_to(self, destination):
        destination = Path(destination)
        if destination.resolve() == self.path.resolve():
            raise ValueError('备份路径不能是当前数据库。')
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = destination.with_name(destination.name + '.' + uuid4().hex + '.tmp')
        try:
            with closing(sqlite3.connect(stage)) as target:
                self.connection.backup(target)
            os.replace(stage, destination)
        finally:
            stage.unlink(missing_ok=True)
        return destination

    @staticmethod
    def validate_backup(source):
        source = Path(source).resolve()
        if not source.is_file():
            raise FileNotFoundError('找不到备份文件。')
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as c:
            if c.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('备份文件损坏。')
            if c.execute('PRAGMA user_version').fetchone()[0] not in (0, 1):
                raise ValueError('备份来自不支持的数据版本。')
            if c.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view') LIMIT 1").fetchone():
                raise ValueError('备份包含不支持的数据库对象。')
            c.execute('SELECT id,name,sort_order,created_at FROM categories').fetchall()
            c.execute('''SELECT id,name,path,item_type,category_id,is_favorite,is_pinned,sort_order,
                         shortcut_target,source_path,created_at,updated_at FROM items''').fetchall()
            c.execute('SELECT key,value FROM settings').fetchall()
            if not c.execute('SELECT 1 FROM categories LIMIT 1').fetchone() or c.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError('备份的分区或引用数据无效。')

    def restore_from(self, source):
        source = Path(source).resolve()
        if source == self.path.resolve():
            raise ValueError('请选择另外的备份文件。')
        self.validate_backup(source)
        stage = self.path.with_name('restore-'+uuid4().hex+'.tmp')
        try:
            with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as origin:
                with closing(sqlite3.connect(stage)) as target:
                    origin.backup(target)
            candidate = Database(stage)
            try:
                candidate.initialize()
                candidate.items()
                candidate.categories()
                with candidate.connection as c:
                    c.execute('DELETE FROM history')
            finally:
                candidate.close()
            self.validate_backup(stage)
            safe = self.path.parent / 'backups' / ('before-restore-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.db')
            self.backup_to(safe)
            self.close()
            os.replace(stage, self.path)
        finally:
            stage.unlink(missing_ok=True)

    @staticmethod
    def _item(row):
        return DesktopItem(**{key: (bool(row[key]) if key in ('is_favorite', 'is_pinned') else row[key])
                              for key in DesktopItem.__dataclass_fields__})
