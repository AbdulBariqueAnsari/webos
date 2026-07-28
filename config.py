import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8080
WEBDAV_PORT = 8081
FILE_PORT = 8082
AGENT_PORT = 8083
WS_PORT = 8084

STORAGE_DIR = os.path.join(BASE_DIR, "storage")
WEB_DIR = os.path.join(BASE_DIR, "web")
APPS_DIR = os.path.join(WEB_DIR, "apps")
DB_PATH = os.path.join(STORAGE_DIR, "webos.db")
USERS_DB = os.path.join(STORAGE_DIR, "users.db")

DEFAULT_USER = "admin"
DEFAULT_PASS = "admin"

AUTO_START_SERVERS = {
    "http": True,
    "webdav": True,
    "file": True,
    "agent": True,
    "websocket": True,
}

EXTERNAL_SERVERS = {}
