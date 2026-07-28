import os
import json
import sqlite3
import threading
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")


class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        os.makedirs(DB_DIR, exist_ok=True)
        self.conn = sqlite3.connect(os.path.join(DB_DIR, "webos.db"), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self._init_tables()

    def _init_tables(self):
        with self.lock:
            c = self.conn.cursor()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TEXT DEFAULT (datetime('now')),
                    last_login TEXT
                );
                CREATE TABLE IF NOT EXISTS files_meta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    size INTEGER DEFAULT 0,
                    is_dir INTEGER DEFAULT 0,
                    mime_type TEXT DEFAULT '',
                    hash TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    created_at TEXT DEFAULT (datetime('now')),
                    modified_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    task TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    result TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now')),
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS apps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    version TEXT DEFAULT '1.0',
                    icon TEXT DEFAULT '📦',
                    category TEXT DEFAULT 'default',
                    enabled INTEGER DEFAULT 1,
                    config TEXT DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    type TEXT DEFAULT 'info',
                    read INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    user_id INTEGER DEFAULT 1
                );
                INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin', 'admin');
                INSERT OR IGNORE INTO settings (key, value) VALUES ('wallpaper', 'default');
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    type TEXT DEFAULT 'todo',
                    created_at TEXT DEFAULT (datetime('now'))
                );
                INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'dark');
            """)
            self.conn.commit()

    def query(self, sql, params=None):
        with self.lock:
            c = self.conn.cursor()
            if params:
                c.execute(sql, params)
            else:
                c.execute(sql)
            return [dict(row) for row in c.fetchall()]

    def execute(self, sql, params=None):
        with self.lock:
            c = self.conn.cursor()
            if params:
                c.execute(sql, params)
            else:
                c.execute(sql)
            self.conn.commit()
            return c.lastrowid

    def get_user(self, username):
        users = self.query("SELECT * FROM users WHERE username = ?", (username,))
        return users[0] if users else None

    def validate_user(self, username, password):
        user = self.get_user(username)
        if user and user["password"] == password:
            self.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (user["id"],))
            return user
        return None

    def add_notification(self, title, message, ntype="info"):
        self.execute(
            "INSERT INTO notifications (title, message, type) VALUES (?, ?, ?)",
            (title, message, ntype),
        )

    def get_notifications(self, limit=50):
        return self.query(
            "SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?", (limit,)
        )

    def get_setting(self, key, default=""):
        rows = self.query("SELECT value FROM settings WHERE key = ?", (key,))
        return rows[0]["value"] if rows else default

    def set_setting(self, key, value):
        self.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )

    def last_id(self):
        with self.lock:
            c = self.conn.cursor()
            return c.lastrowid


db = Database()
