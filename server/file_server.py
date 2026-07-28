import os
import sys
import json
import hashlib
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STORAGE_DIR
from server.storage_manager import resolve_path

FILE_INDEX = {}
FILE_INDEX_LOCK = threading.Lock()


def build_index():
    global FILE_INDEX
    with FILE_INDEX_LOCK:
        FILE_INDEX = {}
        for root, dirs, files in os.walk(STORAGE_DIR):
            for f in files:
                fpath = os.path.join(root, f)
                rel = os.path.relpath(fpath, STORAGE_DIR)
                stat = os.stat(fpath)
                FILE_INDEX[rel] = {
                    "path": fpath,
                    "name": f,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "hash": "",
                }
    print(f"[FileServer] Indexed {len(FILE_INDEX)} files")


def compute_hash(filepath):
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


class FileRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/search":
            query = params.get("q", [""])[0]
            results = []
            with FILE_INDEX_LOCK:
                for rel, info in FILE_INDEX.items():
                    if query.lower() in rel.lower():
                        results.append(info)
                        if len(results) >= 50:
                            break
            self._json_response({"results": results, "query": query})

        elif parsed.path == "/browse":
            subpath = params.get("path", [""])[0]
            base = resolve_path(subpath)
            if not os.path.exists(base):
                self._error(404, "Path not found")
                return
            items = []
            for entry in os.scandir(base):
                items.append({
                    "name": entry.name,
                    "path": os.path.relpath(entry.path, STORAGE_DIR),
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if not entry.is_dir() else 0,
                    "modified": entry.stat().st_mtime,
                })
            self._json_response({"items": items, "path": subpath})

        elif parsed.path == "/hash":
            subpath = params.get("path", [""])[0]
            fpath = resolve_path(subpath)
            if os.path.isfile(fpath):
                h = compute_hash(fpath)
                self._json_response({"hash": h, "path": subpath})
            else:
                self._error(404, "File not found")

        elif parsed.path == "/stats":
            with FILE_INDEX_LOCK:
                total_files = len(FILE_INDEX)
                total_size = sum(i["size"] for i in FILE_INDEX.values())
            self._json_response({
                "total_files": total_files,
                "total_size": total_size,
                "storage": STORAGE_DIR,
            })

        elif parsed.path.startswith("/download/"):
            subpath = parsed.path[len("/download/"):]
            fpath = resolve_path(subpath)
            if os.path.isfile(fpath):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(fpath)}"')
                self.send_header("Content-Length", str(os.path.getsize(fpath)))
                self.end_headers()
                with open(fpath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._error(404, "File not found")
        else:
            self._error(404, "Not found")

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/upload/"):
            subpath = parsed.path[len("/upload/"):]
            fpath = resolve_path(subpath)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            length = int(self.headers.get("Content-Length", 0))
            with open(fpath, "wb") as f:
                f.write(self.rfile.read(length))
            build_index()
            self._json_response({"status": "uploaded", "path": subpath})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/delete/"):
            subpath = parsed.path[len("/delete/"):]
            fpath = resolve_path(subpath)
            if os.path.isfile(fpath):
                os.remove(fpath)
                build_index()
                self._json_response({"status": "deleted"})
            else:
                self._error(404, "Not found")

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _error(self, code, msg):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg}).encode())

    def log_message(self, format, *args):
        pass


class FileServer:
    def __init__(self, host="0.0.0.0", port=8082):
        self.host = host
        self.port = port
        self.server = None

    def start(self):
        build_index()
        self.server = HTTPServer((self.host, self.port), FileRequestHandler)
        print(f"[FileServer] Started on http://{self.host}:{self.port}")
        self.server.serve_forever()

    def stop(self):
        if self.server:
            self.server.shutdown()
