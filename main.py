#!/usr/bin/env python3
"""
Web OS v1.0 — Complete Standalone Operating System
Advanced multi-agent AI system with 12 agents, desktop environment,
device control, real-time updates, ISO boot, and full PC integration
"""

import os, sys, threading, time, signal, socket
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *


# Ensure unbuffered standard output so terminal streaming never freezes
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass


def get_all_ips():
    ips = []
    primary_ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        if primary_ip and not primary_ip.startswith("127."):
            ips.append(primary_ip)
    except Exception:
        pass

    try:
        import psutil
        addrs = psutil.net_if_addrs()
        for iface_name, addr_list in addrs.items():
            for addr in addr_list:
                if addr.family == socket.AF_INET and addr.address:
                    if not addr.address.startswith("127.") and addr.address not in ips:
                        ips.append(addr.address)
    except Exception:
        pass

    if not ips:
        ips.append("127.0.0.1")

    return primary_ip or ips[0], ips


def banner():
    host = socket.gethostname()
    primary_ip, all_ips = get_all_ips()
    line = "=" * 62
    
    print(f"""
    {line}
      Web OS v1.0 — COMPLETE STANDALONE OPERATING SYSTEM
      12 AI Agents | 55+ Apps | Multi-User | ISO Bootable | Live Network
    {line}

    Hostname         : {host}
    Primary LAN IP   : {primary_ip}
    All Detected IPs : {", ".join(all_ips)}

    --------------------------------------------------------------
    SERVER ACCESS URLS (Connect from Local Machine or LAN Network)
    --------------------------------------------------------------
    Local Access     -> http://localhost:{HTTP_PORT}
                     -> http://127.0.0.1:{HTTP_PORT}
    Network (LAN)    -> http://{primary_ip}:{HTTP_PORT}
    Desktop UI       -> http://{primary_ip}:{HTTP_PORT}/desktop
    
    WebDAV Server    -> http://{primary_ip}:{WEBDAV_PORT}
    File Server      -> http://{primary_ip}:{FILE_PORT}
    WebSocket Server -> ws://{primary_ip}:{WS_PORT}
    --------------------------------------------------------------
    Default Login    : admin / admin
    ==============================================================
    """, flush=True)


class ServerThread(threading.Thread):
    def __init__(self, target, name):
        super().__init__(target=target, name=name, daemon=True)
        self._target_fn = target

    def run(self):
        try:
            self._target_fn()
        except Exception as e:
            print(f"  [WARN] [{self.name}] Error: {e}", flush=True)


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


def live_status_monitor(servers):
    count = 0
    while True:
        time.sleep(10)
        count += 1
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            primary_ip, all_ips = get_all_ips()
            now = time.strftime("%H:%M:%S")
            active_list = [name for name, t in servers.items() if t.is_alive()]
            print(f"  [{now}] [STATUS] Active: {', '.join(active_list)} | CPU: {cpu}% | RAM: {mem}% | LAN IP: http://{primary_ip}:{HTTP_PORT}", flush=True)
        except Exception:
            pass


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

    primary_ip, _ = get_all_ips()
    print(f"\n  [OK] All Web OS servers are running continuously!", flush=True)
    print(f"  Local Access  : http://localhost:{HTTP_PORT}", flush=True)
    print(f"  Network Access: http://{primary_ip}:{HTTP_PORT}", flush=True)
    print(f"  Desktop UI    : http://{primary_ip}:{HTTP_PORT}/desktop", flush=True)
    print(f"  Press Ctrl+C to stop. Live status updates will scroll below:\n", flush=True)

    monitor_t = threading.Thread(target=live_status_monitor, args=(servers,), daemon=True)
    monitor_t.start()

    def shutdown(sig, frame):
        print("\n  [STOP] Shutting down Web OS...", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
            for name, t in list(servers.items()):
                if not t.is_alive():
                    print(f"  [RESTART] Restarting {name}...", flush=True)
                    new_t = ServerThread(target=t._target_fn, name=name)
                    new_t.start()
                    servers[name] = new_t
    except KeyboardInterrupt:
        print("\n  [STOP] Goodbye!", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()

