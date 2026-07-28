import sqlite3, json, time, os, threading
from collections import defaultdict

MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(MEMORY_DIR, exist_ok=True)

class AgentMemory:
    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, agent_name="shared"):
        with cls._lock:
            if agent_name not in cls._instances:
                inst = super().__new__(cls)
                inst.agent_name = agent_name
                inst.db_path = os.path.join(MEMORY_DIR, f"memory_{agent_name}.db")
                inst._init_db()
                cls._instances[agent_name] = inst
            return cls._instances[agent_name]

    def _init_db(self):
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, role TEXT, content TEXT,
            timestamp REAL, metadata TEXT
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS memory (
            key TEXT PRIMARY KEY, value TEXT, updated REAL
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, description TEXT, usage_count INTEGER DEFAULT 0,
            last_used REAL
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT UNIQUE, confidence REAL DEFAULT 1.0,
            source TEXT, created REAL
        )""")
        self._conn.commit()

    def remember_conversation(self, session_id, role, content, metadata=None):
        self._conn.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp, metadata) VALUES (?,?,?,?,?)",
            (session_id, role, content, time.time(), json.dumps(metadata or {}))
        )
        self._conn.commit()

    def recall_conversation(self, session_id, limit=50):
        rows = self._conn.execute(
            "SELECT role, content, timestamp FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
        return [{"role": r["role"], "content": r["content"], "time": r["timestamp"]} for r in reversed(rows)]

    def search_memories(self, query, limit=10):
        rows = self._conn.execute(
            "SELECT role, content, timestamp FROM conversations WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        return [{"role": r["role"], "content": r["content"][:500], "time": r["timestamp"]} for r in rows]

    def save_fact(self, fact, source="agent", confidence=1.0):
        self._conn.execute(
            "INSERT OR REPLACE INTO facts (fact, confidence, source, created) VALUES (?,?,?,?)",
            (fact, confidence, source, time.time())
        )
        self._conn.commit()

    def get_facts(self, topic=None, limit=50):
        if topic:
            rows = self._conn.execute(
                "SELECT fact, confidence, source FROM facts WHERE fact LIKE ? ORDER BY confidence DESC LIMIT ?",
                (f"%{topic}%", limit)
            )
        else:
            rows = self._conn.execute(
                "SELECT fact, confidence, source FROM facts ORDER BY confidence DESC LIMIT ?", (limit,)
            )
        return [dict(r) for r in rows.fetchall()]

    def set_preference(self, key, value):
        self._conn.execute(
            "INSERT OR REPLACE INTO memory (key, value, updated) VALUES (?,?,?)",
            (key, json.dumps(value), time.time())
        )
        self._conn.commit()

    def get_preference(self, key, default=None):
        row = self._conn.execute("SELECT value FROM memory WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def log_tool_usage(self, name, description=""):
        self._conn.execute(
            "INSERT INTO tools (name, description, usage_count, last_used) VALUES (?,?,1,?) "
            "ON CONFLICT(id) DO UPDATE SET usage_count=usage_count+1, last_used=? "
            "WHERE name=?",
            (name, description, time.time(), time.time(), name)
        )
        self._conn.commit()

    def get_stats(self):
        convs = self._conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        facts = self._conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        tools = [dict(r) for r in self._conn.execute("SELECT * FROM tools ORDER BY usage_count DESC LIMIT 20").fetchall()]
        return {"conversations": convs, "facts": facts, "top_tools": tools}

    def close(self):
        self._conn.close()
