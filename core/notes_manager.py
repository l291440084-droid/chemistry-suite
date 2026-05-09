"""笔记管理器 — SQLite 后端"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


DB_DIR = Path(__file__).resolve().parent.parent / "notes"


class NotesManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            DB_DIR.mkdir(parents=True, exist_ok=True)
            db_path = str(DB_DIR / "notes.db")
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL DEFAULT 'general',
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                book_filename TEXT DEFAULT '',
                book_page INTEGER DEFAULT 0,
                smiles TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL DEFAULT 'general',
                book_filename TEXT NOT NULL,
                book_page INTEGER NOT NULL DEFAULT 1,
                label TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS formulas_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latex TEXT NOT NULL,
                category TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    # ---- 笔记 CRUD ----

    def add_note(self, subject: str, title: str, content: str,
                 book_filename: str = "", book_page: int = 0,
                 smiles: str = "", tags: str = "") -> int:
        now = datetime.now().isoformat()
        cur = self.conn.execute(
            "INSERT INTO notes (subject, title, content, book_filename,"
            " book_page, smiles, tags, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (subject, title, content, book_filename,
             book_page, smiles, tags, now, now)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_note(self, note_id: int, **kwargs):
        fields = {k: v for k, v in kwargs.items()
                  if k in ("subject", "title", "content", "book_filename",
                           "book_page", "smiles", "tags")}
        if not fields:
            return
        fields["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [note_id]
        self.conn.execute(f"UPDATE notes SET {sets} WHERE id=?", vals)
        self.conn.commit()

    def delete_note(self, note_id: int):
        self.conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        self.conn.commit()

    def get_note(self, note_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM notes WHERE id=?", (note_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_notes(self, subject: str = None, limit: int = 100,
                   offset: int = 0) -> list:
        if subject and subject != "全部":
            rows = self.conn.execute(
                "SELECT * FROM notes WHERE subject=? ORDER BY updated_at DESC"
                " LIMIT ? OFFSET ?",
                (subject, limit, offset)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM notes ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        return [dict(r) for r in rows]

    def search_notes(self, query: str, limit: int = 50) -> list:
        pattern = f"%{query}%"
        rows = self.conn.execute(
            "SELECT * FROM notes WHERE content LIKE ? OR title LIKE ?"
            " OR tags LIKE ? LIMIT ?",
            (pattern, pattern, pattern, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- 书签 CRUD ----

    def add_bookmark(self, subject: str, book_filename: str,
                     book_page: int, label: str = "") -> int:
        now = datetime.now().isoformat()
        cur = self.conn.execute(
            "INSERT INTO bookmarks (subject, book_filename, book_page, label, created_at)"
            " VALUES (?,?,?,?,?)",
            (subject, book_filename, book_page, label, now)
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_bookmark(self, bm_id: int):
        self.conn.execute("DELETE FROM bookmarks WHERE id=?", (bm_id,))
        self.conn.commit()

    def list_bookmarks(self, subject: str = None) -> list:
        if subject:
            rows = self.conn.execute(
                "SELECT * FROM bookmarks WHERE subject=? ORDER BY created_at DESC",
                (subject,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM bookmarks ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # ---- 公式收藏 ----

    def add_favorite_formula(self, latex: str, category: str = ""):
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO formulas_favorites (latex, category, created_at)"
            " VALUES (?,?,?)", (latex, category, now)
        )
        self.conn.commit()

    def list_favorite_formulas(self) -> list:
        rows = self.conn.execute(
            "SELECT * FROM formulas_favorites ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
