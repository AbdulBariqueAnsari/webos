#!/usr/bin/env python3
"""
Web OS v1.0 — Complete Standalone Operating System
Advanced multi-agent AI system with 12 agents, desktop environment,
device control, real-time updates, ISO boot, and full PC integration
"""

import os, sys, threading, time, signal, socket
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *


def banner():
    host = socket.gethostname()
    # Safe banner without Unicode box drawing (Windows compatible)
    line = "=" * 50
    print(f"""
    {line}
      Web OS v1.0 - COMPLETE EDITION
      Full Standalone Operating System
      12 AI Agents | 55+ Apps | Multi-User | ISO Bootable
    {line}

    Host: {host}
    ------------ --------------------------------
    HTTP Server     -> http://localhost:{HTTP_PORT}
    WebDAV Server   -> http://localhost:{WEBDAV_PORT}
    File Server     -> http://localhost:{FILE_PORT}
    WebSocket       -> ws://localhost:{WS_PORT}
    ------------ --------------------------------
    Login: admin / admin
    Desktop: http://localhost:{HTTP_PORT}/desktop
    """)


class ServerThread(threading.Thread):
    def __init__(self, target, name):
        super().__init__(target=target, name=name, daemon=True)
        self._target_fn = target

    def run(self):
        try:
            self._target_fn()
        except Exception as e:
            print(f"  [WARN] [{self.name}] Error: {e}")


def start_http():
    from server.http_server import start
    start(host=HTTP_HOST, port=HTTP_PORT)


def start_webdav():
    from server.webdav_server import WebDAVServer
    WebDAVServer(host=HTTP_HOST, port=WEBDAV_PORT).start()


def start_file():
    from server.file_server import FileServer
    FileServer(host=HTTP_HOST, port=FILE_PORT).start()


def start_ws():
    from server.ws_server import start_ws_server
    start_ws_server(host=HTTP_HOST, port=WS_PORT)


def main():
    banner()
    servers = {}

    services = [
        ("HTTP", start_http, AUTO_START_SERVERS.get("http", True)),
        ("WebDAV", start_webdav, AUTO_START_SERVERS.get("webdav", True)),
        ("File", start_file, AUTO_START_SERVERS.get("file", True)),
        ("WebSocket", start_ws, AUTO_START_SERVERS.get("websocket", True)),
    ]

    for name, fn, enabled in services:
        if enabled:
            t = ServerThread(target=fn, name=name)
            t.start()
            servers[name] = t
            time.sleep(0.5)

    print(f"\n  [OK] All servers started! Open http://localhost:{HTTP_PORT}")
    print(f"  Press Ctrl+C to stop\n")

    def shutdown(sig, frame):
        print("\n  [STOP] Shutting down Web OS...")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
            for name, t in list(servers.items()):
                if not t.is_alive():
                    print(f"  [RESTART] Restarting {name}...")
                    new_t = ServerThread(target=t._target_fn, name=name)
                    new_t.start()
                    servers[name] = new_t
    except KeyboardInterrupt:
        print("\n  [STOP] Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
