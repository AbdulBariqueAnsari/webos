import os, json, socket, requests, subprocess
from datetime import datetime

CONNECTORS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "connectors.json")


class ServerConnector:
    def __init__(self):
        self.connections = self._load()

    def _load(self):
        if os.path.exists(CONNECTORS_FILE):
            try:
                with open(CONNECTORS_FILE) as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        os.makedirs(os.path.dirname(CONNECTORS_FILE), exist_ok=True)
        with open(CONNECTORS_FILE, "w") as f:
            json.dump(self.connections, f, indent=2)

    def list_connections(self):
        return self.connections

    def connect(self, name, config):
        ctype = config.get("type", "http")
        url = config.get("url", "")
        result = {"status": "error", "message": "Not implemented"}

        handlers = {
            "http": self._http_connect,
            "https": self._http_connect,
            "webdav": self._webdav_connect,
            "ssh": self._ssh_connect,
            "ftp": self._ftp_connect,
            "samba": self._smb_connect,
            "nfs": self._nfs_connect,
            "mysql": self._mysql_connect,
            "postgresql": self._postgres_connect,
            "redis": self._redis_connect,
            "mqtt": self._mqtt_connect,
        }

        handler = handlers.get(ctype)
        if handler:
            result = handler(config)

        if result.get("status") == "ok":
            conn = {"name": name, "type": ctype, "url": url, "config": config,
                    "connected": True, "last_connected": datetime.now().isoformat()}
            self._upsert(conn)
            self._save()

        return result

    def _upsert(self, conn):
        for i, c in enumerate(self.connections):
            if c["name"] == conn["name"]:
                self.connections[i] = conn
                return
        self.connections.append(conn)

    def _http_connect(self, config):
        url = config.get("url", "")
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "WebOS/2.0"})
            return {"status": "ok", "code": r.status_code, "headers": dict(r.headers), "preview": r.text[:200]}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _webdav_connect(self, config):
        url = config.get("url", "")
        auth = (config.get("username", ""), config.get("password", "")) if config.get("username") else None
        try:
            r = requests.request("PROPFIND", url, auth=auth, headers={"Depth": "1"}, timeout=10)
            return {"status": "ok", "code": r.status_code, "type": "WebDAV"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _ssh_connect(self, config):
        host = config.get("url", "").replace("ssh://", "").split("/")[0]
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, port=config.get("port", 22), username=config.get("username", "root"),
                           password=config.get("password", ""), timeout=10)
            _, stdout, _ = client.exec_command("uname -a")
            info = stdout.read().decode().strip()
            client.close()
            return {"status": "ok", "system": info}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _ftp_connect(self, config):
        host = config.get("url", "").replace("ftp://", "").split("/")[0]
        try:
            import ftplib
            ftp = ftplib.FTP(host, timeout=10)
            ftp.login(config.get("username", "anonymous"), config.get("password", ""))
            files = ftp.nlst()[:20]
            ftp.quit()
            return {"status": "ok", "files": files}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _smb_connect(self, config):
        host = config.get("url", "").replace("smb://", "").split("/")[0]
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            r = s.connect_ex((host, config.get("port", 445)))
            s.close()
            if r == 0:
                return {"status": "ok", "message": f"SMB reachable on {host}:445"}
            return {"status": "error", "message": "SMB port closed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _nfs_connect(self, config):
        url = config.get("url", "")
        try:
            r = subprocess.run(["showmount", "-e", url], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return {"status": "ok", "exports": r.stdout.strip()}
            return {"status": "error", "message": r.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _mysql_connect(self, config):
        try:
            import mysql.connector
            conn = mysql.connector.connect(host=config.get("url"),
                user=config.get("username", "root"),
                password=config.get("password", ""),
                port=config.get("port", 3306),
                connection_timeout=10,
            )
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            ver = cursor.fetchone()
            conn.close()
            return {"status": "ok", "version": ver[0] if ver else "N/A"}
        except ImportError:
            return {"status": "error", "message": "mysql-connector not installed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _postgres_connect(self, config):
        try:
            import psycopg2
            conn = psycopg2.connect(host=config.get("url"),
                user=config.get("username", "postgres"),
                password=config.get("password", ""),
                port=config.get("port", 5432),
                connect_timeout=10,
            )
            cur = conn.cursor()
            cur.execute("SELECT version()")
            ver = cur.fetchone()
            conn.close()
            return {"status": "ok", "version": ver[0] if ver else "N/A"}
        except ImportError:
            return {"status": "error", "message": "psycopg2 not installed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _redis_connect(self, config):
        try:
            import redis
            r = redis.Redis(host=config.get("url"), port=config.get("port", 6379),
                           password=config.get("password", ""), socket_timeout=5)
            info = r.info()
            return {"status": "ok", "version": info.get("redis_version", "unknown"),
                    "uptime": info.get("uptime_in_seconds", 0)}
        except ImportError:
            return {"status": "error", "message": "redis not installed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _mqtt_connect(self, config):
        try:
            import paho.mqtt.client as mqtt
            client = mqtt.Client()
            client.connect(config.get("url"), config.get("port", 1883), 5)
            client.disconnect()
            return {"status": "ok", "message": "MQTT broker reachable"}
        except ImportError:
            return {"status": "error", "message": "paho-mqtt not installed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def fetch_data(self, name, query):
        conn = next((c for c in self.connections if c["name"] == name), None)
        if not conn:
            return {"status": "error", "message": f"Connector '{name}' not found"}
        try:
            if conn["type"] in ("http", "https"):
                url = conn["url"]
                if query:
                    url = f"{url.rstrip('/')}/{query.lstrip('/')}"
                r = requests.get(url, timeout=10)
                return {"status": "ok", "data": r.text[:2000]}
            if conn["type"] == "webdav":
                r = requests.request("PROPFIND", conn["url"], headers={"Depth": "1"}, timeout=10)
                return {"status": "ok", "data": r.text[:2000]}
            return {"status": "error", "message": f"Fetch not supported for {conn['type']}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
