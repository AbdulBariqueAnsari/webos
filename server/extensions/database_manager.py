import os, json, sqlite3, traceback


class DatabaseManager:
    def __init__(self):
        self.connections = {}

    def connect(self, db_type, config):
        try:
            if db_type == "sqlite":
                path = config.get("path", "")
                if not os.path.isfile(path):
                    return {"status": "error", "message": f"File not found: {path}"}
                conn = sqlite3.connect(path)
                conn.row_factory = sqlite3.Row
                cid = f"sqlite_{len(self.connections)}"
                self.connections[cid] = conn
                return {"status": "ok", "id": cid, "type": "sqlite"}

            elif db_type == "mysql":
                import mysql.connector
                conn = mysql.connector.connect(
                    host=config.get("host", "localhost"),
                    port=config.get("port", 3306),
                    user=config.get("user", "root"),
                    password=config.get("password", ""),
                    database=config.get("database", ""),
                )
                cid = f"mysql_{len(self.connections)}"
                self.connections[cid] = conn
                return {"status": "ok", "id": cid, "type": "mysql"}

            elif db_type == "postgresql":
                import psycopg2
                conn = psycopg2.connect(
                    host=config.get("host", "localhost"),
                    port=config.get("port", 5432),
                    user=config.get("user", "postgres"),
                    password=config.get("password", ""),
                    dbname=config.get("database", ""),
                )
                cid = f"pg_{len(self.connections)}"
                self.connections[cid] = conn
                return {"status": "ok", "id": cid, "type": "postgresql"}

            return {"status": "error", "message": f"Unsupported type: {db_type}"}

        except ImportError as e:
            return {"status": "error", "message": f"Driver not installed: {e}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def query(self, conn_id, sql, params=None):
        conn = self.connections.get(conn_id)
        if not conn:
            return {"status": "error", "message": "Connection not found"}
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            if sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("PRAGMA") or sql.strip().upper().startswith("SHOW") or sql.strip().upper().startswith("DESCRIBE") or sql.strip().upper().startswith("EXPLAIN"):
                rows = [dict(row) for row in cursor.fetchall()]
                cols = [desc[0] for desc in cursor.description] if cursor.description else []
                return {"status": "ok", "columns": cols, "rows": rows, "count": len(rows)}
            else:
                conn.commit()
                return {"status": "ok", "affected": cursor.rowcount, "last_id": cursor.lastrowid}

        except Exception as e:
            return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

    def tables(self, conn_id):
        conn = self.connections.get(conn_id)
        if not conn:
            return {"status": "error", "message": "Connection not found"}
        try:
            cursor = conn.cursor()
            if isinstance(conn, sqlite3.Connection):
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            else:
                cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            return {"status": "ok", "tables": tables}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def disconnect(self, conn_id):
        conn = self.connections.pop(conn_id, None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
            return True
        return False

    def list_connections(self):
        return [{"id": cid, "type": type(conn).__name__} for cid, conn in self.connections.items()]


db_manager = DatabaseManager()
