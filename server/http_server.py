import os, sys, json, subprocess, psutil, platform, shutil, socket, hashlib, threading, time, uuid, traceback, mimetypes, struct, zipfile, tarfile, io, base64, re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WEB_DIR, STORAGE_DIR, HTTP_PORT
from server.database import db
from server.auth import login_required, init_auth_routes
from server.ws_server import WebSocketServer
from server.extensions.docker_manager import DockerManager
from server.extensions.database_manager import db_manager
from server.extensions.file_share import file_share
from server.extensions.code_runner import code_runner
from server.extensions.backup_manager import backup_manager
from server.extensions.plugin_loader import PluginLoader
from server.storage_manager import (
    list_dir, read_file, write_file, delete_file, permanent_delete,
    move_file, copy_file, search_files, file_info, resolve_path,
    trash_list, trash_restore, trash_empty,
    bookmarks_list, bookmark_add, bookmark_remove,
    get_recent,
)
from agents.agent_manager_hub import AgentHub

app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")
app.secret_key = os.urandom(32).hex()
CORS(app, supports_credentials=True)

hub = AgentHub()
init_auth_routes(app, db)

# Plugin system
plugin_loader = PluginLoader(app=app, hub=hub)
plugin_loader.discover()


# ─── SYSTEM ───────────────────────────────────────────────────
def get_system_stats():
    cpu = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()
    mem = psutil.virtual_memory()
    disk = {"total": 0, "used": 0, "percent": 0, "free": 0}
    try:
        d = psutil.disk_usage("/")
        disk = {"total": d.total, "used": d.used, "percent": d.percent, "free": d.free}
    except Exception:
        try:
            d = psutil.disk_usage("C:\\")
            disk = {"total": d.total, "used": d.used, "percent": d.percent, "free": d.free}
        except Exception:
            pass
    temps = []
    try:
        temps = [t.current for t in psutil.sensors_temperatures().get("coretemp", [])]
    except Exception:
        pass
    load_avg = [0, 0, 0]
    try:
        if hasattr(psutil, "getloadavg"):
            load_avg = [round(x, 2) for x in psutil.getloadavg()]
    except Exception:
        pass
    net_io = {"bytes_sent": 0, "bytes_recv": 0}
    try:
        net = psutil.net_io_counters()
        net_io = {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv}
    except Exception:
        pass
    uptime = 0
    try:
        uptime = time.time() - psutil.boot_time()
    except Exception:
        pass
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "cpu": {"percent": cpu, "count": cpu_count, "temp": max(temps) if temps else 0},
        "memory": {"total": mem.total, "used": mem.used, "percent": mem.percent, "available": mem.available},
        "disk": disk,
        "network": net_io,
        "uptime": uptime,
        "load_avg": load_avg,
    }


def get_processes(sort_by="cpu", limit=100):
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status", "create_time"]):
        try:
            procs.append(p.info)
        except Exception:
            pass
    reverse = sort_by in ("cpu", "memory_percent")
    procs.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=reverse)
    return procs[:limit]


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "login.html")


@app.route("/desktop")
def desktop():
    return send_from_directory(WEB_DIR, "desktop.html")


@app.route("/api/system/stats")
@login_required
def api_system_stats():
    return jsonify(get_system_stats())


@app.route("/api/system/processes")
@login_required
def api_system_processes():
    sort = request.args.get("sort", "cpu")
    return jsonify({"processes": get_processes(sort)})


@app.route("/api/system/kill", methods=["POST"])
@login_required
def api_system_kill():
    data = request.json or {}
    pid = data.get("pid")
    try:
        p = psutil.Process(pid)
        name = p.name()
        p.terminate()
        db.add_notification("Process Killed", f"{name} ({pid})", "warning")
        return jsonify({"status": "killed", "pid": pid})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/system/services")
@login_required
def api_system_services():
    services = {}
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            conns = proc.connections()
            for conn in conns:
                if conn.status == "LISTEN":
                    key = f"{proc.info['name']}:{conn.laddr.port}"
                    services[key] = {"pid": proc.info["pid"], "name": proc.info["name"], "port": conn.laddr.port}
        except Exception:
            pass
    return jsonify(services)


@app.route("/api/system/diskio")
@login_required
def api_disk_io():
    try:
        io = psutil.disk_io_counters()
        return jsonify({"read_bytes": io.read_bytes, "write_bytes": io.write_bytes, "read_count": io.read_count, "write_count": io.write_count})
    except Exception:
        return jsonify({"error": "Not available"})


@app.route("/api/system/network")
@login_required
def api_network_io():
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    result = {}
    for name, addr_list in addrs.items():
        s = stats.get(name)
        result[name] = {
            "addresses": [{"address": a.address, "family": str(a.family)} for a in addr_list],
            "isup": s.isup if s else False,
            "speed": s.speed if s else 0,
        }
    return jsonify(result)


def get_full_network_details():
    hostname = socket.gethostname()
    all_ips = []
    interfaces = []

    primary_ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for name, addr_list in addrs.items():
            s = stats.get(name)
            iface_info = {
                "name": name,
                "is_up": s.isup if s else False,
                "speed": s.speed if s else 0,
                "ips": [],
                "mac": None
            }
            for a in addr_list:
                if a.family == socket.AF_INET:
                    iface_info["ips"].append({"ip": a.address, "netmask": a.netmask, "type": "IPv4"})
                    if a.address not in all_ips and not a.address.startswith("127."):
                        all_ips.append(a.address)
                elif hasattr(socket, "AF_INET6") and a.family == socket.AF_INET6:
                    iface_info["ips"].append({"ip": a.address, "type": "IPv6"})
                elif hasattr(psutil, "AF_LINK") and a.family == psutil.AF_LINK:
                    iface_info["mac"] = a.address
            interfaces.append(iface_info)
    except Exception:
        pass

    if primary_ip and primary_ip not in all_ips:
        all_ips.insert(0, primary_ip)

    if not all_ips:
        all_ips.append("127.0.0.1")

    main_ip = primary_ip or (all_ips[0] if all_ips else "127.0.0.1")

    access_urls = {
        "localhost": f"http://localhost:{HTTP_PORT}",
        "primary_lan": f"http://{main_ip}:{HTTP_PORT}",
        "hostname": f"http://{hostname}:{HTTP_PORT}",
        "desktop": f"http://{main_ip}:{HTTP_PORT}/desktop",
        "lan_urls": [f"http://{ip}:{HTTP_PORT}" for ip in all_ips],
        "webdav": f"http://{main_ip}:8081",
        "file": f"http://{main_ip}:8082",
        "ws": f"ws://{main_ip}:8084"
    }

    net_io = {}
    try:
        nio = psutil.net_io_counters()
        net_io = {"bytes_sent": nio.bytes_sent, "bytes_recv": nio.bytes_recv, "packets_sent": nio.packets_sent, "packets_recv": nio.packets_recv}
    except Exception:
        pass

    return {
        "hostname": hostname,
        "primary_ip": main_ip,
        "all_ips": all_ips,
        "interfaces": interfaces,
        "access_urls": access_urls,
        "http_port": HTTP_PORT,
        "ws_port": 8084,
        "net_io": net_io,
        "timestamp": datetime.now().isoformat()
    }


@app.route("/api/system/network-details")
def api_network_details():
    return jsonify(get_full_network_details())



# ─── TERMINAL ─────────────────────────────────────────────────
@app.route("/api/terminal", methods=["POST"])
@login_required
def api_terminal():
    data = request.json or {}
    cmd = data.get("cmd", "")
    if not cmd:
        return jsonify({"error": "No command"}), 400
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return jsonify({"stdout": result.stdout, "stderr": result.stderr, "rc": result.returncode})
    except subprocess.TimeoutExpired:
        return jsonify({"stdout": "", "stderr": "Command timed out", "rc": -1})
    except Exception as e:
        return jsonify({"stdout": "", "stderr": str(e), "rc": -1})


# ─── FILES (using storage_manager) ──────────────────────────
@app.route("/api/files/list", methods=["POST"])
@login_required
def api_files_list():
    data = request.json or {}
    return jsonify(list_dir(data.get("path", "")))


@app.route("/api/files/read", methods=["POST"])
@login_required
def api_files_read():
    data = request.json or {}
    return jsonify(read_file(data.get("path", "")))


@app.route("/api/files/write", methods=["POST"])
@login_required
def api_files_write():
    data = request.json or {}
    return jsonify(write_file(data.get("path", ""), data.get("content", "")))


@app.route("/api/files/upload", methods=["POST"])
@login_required
def api_files_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    dest = resolve_path(request.form.get("path", ""))
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, f.filename)
    f.save(path)
    WebSocketServer.notify("File Uploaded", f.filename, "success")
    return jsonify({"status": "ok", "filename": f.filename, "path": path})


@app.route("/api/files/delete", methods=["POST"])
@login_required
def api_files_delete():
    data = request.json or {}
    return jsonify(delete_file(data.get("path", "")))


@app.route("/api/files/delete-permanent", methods=["POST"])
@login_required
def api_files_delete_perm():
    data = request.json or {}
    return jsonify(permanent_delete(data.get("path", "")))


@app.route("/api/files/mkdir", methods=["POST"])
@login_required
def api_files_mkdir():
    data = request.json or {}
    full = resolve_path(data.get("path", ""))
    try:
        os.makedirs(full, exist_ok=True)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/files/move", methods=["POST"])
@login_required
def api_files_move():
    data = request.json or {}
    return jsonify(move_file(data.get("src", ""), data.get("dst", "")))


@app.route("/api/files/copy", methods=["POST"])
@login_required
def api_files_copy():
    data = request.json or {}
    return jsonify(copy_file(data.get("src", ""), data.get("dst", "")))


@app.route("/api/files/search", methods=["POST"])
@login_required
def api_files_search():
    data = request.json or {}
    return jsonify(search_files(data.get("q", ""), data.get("path", "")))


@app.route("/api/files/info", methods=["POST"])
@login_required
def api_file_info():
    data = request.json or {}
    return jsonify(file_info(data.get("path", "")))


@app.route("/api/files/preview/<path:filepath>")
@login_required
def api_file_preview(filepath):
    full = resolve_path(filepath)
    if not os.path.isfile(full):
        return jsonify({"error": "Not found"}), 404
    mime_type, _ = mimetypes.guess_type(full)
    if mime_type and mime_type.startswith("image/"):
        return send_file(full, mimetype=mime_type)
    return send_file(full)


@app.route("/api/files/download/<path:filepath>")
@login_required
def api_file_download(filepath):
    full = resolve_path(filepath)
    if not os.path.isfile(full):
        return jsonify({"error": "Not found"}), 404
    return send_file(full, as_attachment=True, download_name=os.path.basename(full))


# ─── RECYCLE BIN ─────────────────────────────
@app.route("/api/trash/list")
@login_required
def api_trash_list():
    return jsonify({"items": trash_list()})


@app.route("/api/trash/restore", methods=["POST"])
@login_required
def api_trash_restore():
    data = request.json or {}
    return jsonify(trash_restore(data.get("name", "")))


@app.route("/api/trash/empty", methods=["POST"])
@login_required
def api_trash_empty():
    return jsonify(trash_empty())


# ─── BOOKMARKS ───────────────────────────────
@app.route("/api/bookmarks/list")
@login_required
def api_bookmarks_list():
    return jsonify({"bookmarks": bookmarks_list()})


@app.route("/api/bookmarks/add", methods=["POST"])
@login_required
def api_bookmarks_add():
    data = request.json or {}
    return jsonify(bookmark_add(data.get("path", ""), data.get("name", "")))


@app.route("/api/bookmarks/remove", methods=["POST"])
@login_required
def api_bookmarks_remove():
    data = request.json or {}
    return jsonify(bookmark_remove(data.get("path", "")))


# ─── RECENT FILES ────────────────────────────
@app.route("/api/files/recent")
@login_required
def api_files_recent():
    return jsonify({"recent": get_recent()})


# ─── AGENTS ───────────────────────────────────────────────────
@app.route("/api/agents/list")
@login_required
def api_agents_list():
    return jsonify({"agents": hub.list_agents(), "active_tasks": hub.list_tasks()})


@app.route("/api/agents/run", methods=["POST"])
@login_required
def api_agents_run():
    data = request.json or {}
    result = hub.run_agent(data.get("agent", ""), data.get("task", ""))
    return jsonify({"result": result})


@app.route("/api/agents/message", methods=["POST"])
@login_required
def api_agents_message():
    data = request.json or {}
    result = hub.process_message(data.get("message", ""))
    return jsonify({"result": result})


@app.route("/api/agents/broadcast", methods=["POST"])
@login_required
def api_agents_broadcast():
    data = request.json or {}
    results = hub.broadcast(data.get("message", ""))
    return jsonify({"results": results})


@app.route("/api/agents/plan", methods=["POST"])
@login_required
def api_agents_plan():
    data = request.json or {}
    goal = data.get("goal", "")
    plan = hub.create_plan(goal)
    return jsonify({"plan": plan})


@app.route("/api/agents/tasks")
@login_required
def api_agent_tasks():
    tasks = db.query("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50")
    return jsonify({"tasks": tasks})


# ─── DEVICES ──────────────────────────────────────────────────
@app.route("/api/devices/list")
@login_required
def api_devices_list():
    from devices.device_manager import DeviceManager
    dm = DeviceManager()
    return jsonify({"devices": dm.list_devices()})


@app.route("/api/devices/scan", methods=["POST"])
@login_required
def api_devices_scan():
    from devices.device_manager import DeviceManager
    dm = DeviceManager()
    devices = dm.scan_network()
    count = len(devices)
    WebSocketServer.notify("Network Scan", f"Found {count} devices", "info")
    return jsonify({"devices": devices})


@app.route("/api/devices/control", methods=["POST"])
@login_required
def api_devices_control():
    data = request.json or {}
    from devices.device_manager import DeviceManager
    dm = DeviceManager()
    result = dm.control_device(data.get("device_id", ""), data.get("action", ""), data.get("params", {}))
    return jsonify({"result": result})


@app.route("/api/devices/wol", methods=["POST"])
@login_required
def api_device_wol():
    data = request.json or {}
    mac = data.get("mac", "")
    if not mac:
        return jsonify({"error": "MAC required"}), 400
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    magic = b"\xff" * 6 + mac_bytes * 16
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic, ("255.255.255.255", 9))
        sock.close()
        return jsonify({"status": "wol_sent", "mac": mac})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── CONNECTORS ───────────────────────────────────────────────
@app.route("/api/connectors/list")
@login_required
def api_connectors_list():
    from connectors.server_connector import ServerConnector
    sc = ServerConnector()
    return jsonify({"connectors": sc.list_connections()})


@app.route("/api/connectors/connect", methods=["POST"])
@login_required
def api_connectors_connect():
    data = request.json or {}
    from connectors.server_connector import ServerConnector
    sc = ServerConnector()
    result = sc.connect(data.get("name", ""), data.get("config", {}))
    if result.get("status") == "ok":
        WebSocketServer.notify("Connected", data.get("name", ""), "success")
    return jsonify({"result": result})


@app.route("/api/connectors/fetch", methods=["POST"])
@login_required
def api_connectors_fetch():
    data = request.json or {}
    from connectors.server_connector import ServerConnector
    sc = ServerConnector()
    result = sc.fetch_data(data.get("connector", ""), data.get("query", ""))
    return jsonify({"result": result})


# ─── NOTIFICATIONS ────────────────────────────────────────────
@app.route("/api/notifications/db")
@login_required
def api_db_notifications():
    return jsonify({"notifications": db.get_notifications()})



@app.route("/api/notifications/read", methods=["POST"])
@login_required
def api_notifications_read():
    data = request.json or {}
    nid = data.get("id")
    if nid:
        db.execute("UPDATE notifications SET read = 1 WHERE id = ?", (nid,))
    else:
        db.execute("UPDATE notifications SET read = 1")
    return jsonify({"status": "ok"})


# ─── SETTINGS ─────────────────────────────────────────────────
@app.route("/api/settings")
@login_required
def api_settings():
    rows = db.query("SELECT key, value FROM settings")
    settings = {r["key"]: r["value"] for r in rows}
    return jsonify(settings)


@app.route("/api/settings/set", methods=["POST"])
@login_required
def api_settings_set():
    data = request.json or {}
    key, value = data.get("key", ""), data.get("value", "")
    if key:
        db.set_setting(key, value)
        return jsonify({"status": "ok"})
    return jsonify({"error": "Key required"}), 400


# ─── SYSTEM COMMANDS ──────────────────────────────────────────
@app.route("/api/system/shutdown", methods=["POST"])
@login_required
def api_shutdown():
    delay = request.json.get("delay", 1) if request.json else 1
    threading.Timer(delay, os._exit, [0]).start()
    return jsonify({"status": "shutting_down", "delay": delay})


@app.route("/api/system/restart", methods=["POST"])
@login_required
def api_restart():
    delay = request.json.get("delay", 1) if request.json else 1
    threading.Timer(delay, lambda: os.execv(sys.executable, [sys.executable] + sys.argv)).start()
    return jsonify({"status": "restarting", "delay": delay})


@app.route("/api/system/endpoint")
@login_required
def api_endpoints():
    rules = []
    for rule in app.url_map.iter_rules():
        rules.append({"endpoint": rule.endpoint, "methods": list(rule.methods - {"OPTIONS", "HEAD"}), "path": rule.rule})
    return jsonify({"endpoints": rules})


# ══════════════════════════════════════════════
#  ADVANCED EXTENSIONS
# ══════════════════════════════════════════════

docker_mgr = DockerManager()

# ─── DOCKER ──────────────────────────────────
@app.route("/api/docker/status")
@login_required
def api_docker_status():
    return jsonify({"available": docker_mgr.available})

@app.route("/api/docker/containers")
@login_required
def api_docker_containers():
    all_flag = request.args.get("all", "false").lower() == "true"
    return jsonify(docker_mgr.list_containers(all=all_flag))

@app.route("/api/docker/container/<container_id>/<action>", methods=["POST"])
@login_required
def api_docker_container_action(container_id, action):
    return jsonify(docker_mgr.container_action(container_id, action))

@app.route("/api/docker/container/<container_id>/logs")
@login_required
def api_docker_container_logs(container_id):
    tail = request.args.get("tail", 50, type=int)
    return jsonify(docker_mgr.container_logs(container_id, tail))

@app.route("/api/docker/container/<container_id>/stats")
@login_required
def api_docker_container_stats(container_id):
    return jsonify(docker_mgr.container_stats(container_id))

@app.route("/api/docker/images")
@login_required
def api_docker_images():
    return jsonify(docker_mgr.list_images())

@app.route("/api/docker/images/pull", methods=["POST"])
@login_required
def api_docker_pull():
    data = request.json or {}
    return jsonify(docker_mgr.pull_image(data.get("image", "")))

@app.route("/api/docker/info")
@login_required
def api_docker_info():
    return jsonify(docker_mgr.system_info())


# ─── DATABASE MANAGER ────────────────────────
@app.route("/api/db/connect", methods=["POST"])
@login_required
def api_db_connect():
    data = request.json or {}
    return jsonify(db_manager.connect(data.get("type", "sqlite"), data.get("config", {})))

@app.route("/api/db/query", methods=["POST"])
@login_required
def api_db_query():
    data = request.json or {}
    return jsonify(db_manager.query(data.get("conn_id", ""), data.get("sql", "")))

@app.route("/api/db/tables", methods=["POST"])
@login_required
def api_db_tables():
    data = request.json or {}
    return jsonify(db_manager.tables(data.get("conn_id", "")))

@app.route("/api/db/disconnect", methods=["POST"])
@login_required
def api_db_disconnect():
    data = request.json or {}
    db_manager.disconnect(data.get("conn_id", ""))
    return jsonify({"status": "ok"})

@app.route("/api/db/connections")
@login_required
def api_db_connections():
    return jsonify({"connections": db_manager.list_connections()})


# ─── FILE SHARING ────────────────────────────
@app.route("/api/shares/create", methods=["POST"])
@login_required
def api_share_create():
    data = request.json or {}
    return jsonify(file_share.create(
        data.get("filepath", ""),
        data.get("expiry_hours", 24),
        data.get("password", ""),
    ))

@app.route("/api/shares/list")
@login_required
def api_shares_list():
    return jsonify({"shares": file_share.list()})

@app.route("/api/shares/<share_id>/delete", methods=["POST"])
@login_required
def api_share_delete(share_id):
    return jsonify(file_share.delete(share_id))

@app.route("/api/shares/<share_id>")
def api_share_get(share_id):
    result = file_share.download(share_id)
    if result["status"] == "ok":
        return send_file(result["filepath"], as_attachment=True, download_name=result["filename"])
    return jsonify(result), 404


# ─── CODE RUNNER ─────────────────────────────
@app.route("/api/code/run", methods=["POST"])
@login_required
def api_code_run():
    data = request.json or {}
    lang = data.get("lang", "python")
    code = data.get("code", "")
    timeout = data.get("timeout", 10)

    if lang == "python":
        return jsonify(code_runner.run_python(code, timeout))
    elif lang == "javascript":
        return jsonify(code_runner.run_javascript(code, timeout))
    elif lang == "shell":
        return jsonify(code_runner.run_shell(code, timeout))
    return jsonify({"status": "error", "stdout": "", "stderr": f"Unsupported language: {lang}", "returncode": -1})


# ─── BACKUP ──────────────────────────────────
@app.route("/api/backup/create", methods=["POST"])
@login_required
def api_backup_create():
    data = request.json or {}
    return jsonify(backup_manager.create_backup(data.get("name", ""), data.get("paths")))

@app.route("/api/backup/list")
@login_required
def api_backup_list():
    return jsonify({"backups": backup_manager.list_backups()})

@app.route("/api/backup/restore", methods=["POST"])
@login_required
def api_backup_restore():
    data = request.json or {}
    return jsonify(backup_manager.restore_backup(data.get("name", "")))

@app.route("/api/backup/delete", methods=["POST"])
@login_required
def api_backup_delete():
    data = request.json or {}
    return jsonify(backup_manager.delete_backup(data.get("name", "")))

@app.route("/api/backup/schedule", methods=["POST"])
@login_required
def api_backup_schedule():
    data = request.json or {}
    return jsonify(backup_manager.schedule(data.get("interval_hours", 24), data.get("paths")))

@app.route("/api/backup/schedule/stop", methods=["POST"])
@login_required
def api_backup_schedule_stop():
    return jsonify(backup_manager.stop_schedule())


# ─── PLUGINS ─────────────────────────────────
@app.route("/api/plugins/list")
@login_required
def api_plugins_list():
    return jsonify({"plugins": plugin_loader.list_plugins()})

@app.route("/api/plugins/reload", methods=["POST"])
@login_required
def api_plugins_reload():
    plugin_loader.reload_all()
    return jsonify({"status": "ok", "plugins": plugin_loader.list_plugins()})


# ─── REAL-TIME CHAT ──────────────────────────
@app.route("/api/chat/send", methods=["POST"])
@login_required
def api_chat_send():
    data = request.json or {}
    user = request.username
    message = data.get("message", "")
    channel = data.get("channel", "general")
    if message.strip():
        payload = {
            "type": "chat",
            "user": user,
            "message": message.strip(),
            "channel": channel,
            "time": datetime.now().isoformat(),
        }
        WebSocketServer.broadcast(payload, channel=channel)
        return jsonify({"status": "sent", "payload": payload})
    return jsonify({"error": "Empty message"}), 400


# ─── API PLAYGROUND ──────────────────────────
@app.route("/api/playground/request", methods=["POST", "GET", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
@login_required
def api_playground():
    data = request.json or {}
    method = data.get("method", request.method).upper()
    url = data.get("url", "")
    headers = data.get("headers", {})
    body = data.get("body", "")
    body_type = data.get("body_type", "json")

    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        import requests as req_lib
        req_headers = {"User-Agent": "WebOS-Playground/2.0", **headers}

        start = time.time()
        if method in ("GET", "HEAD", "OPTIONS"):
            r = req_lib.request(method, url, headers=req_headers, timeout=30)
        elif body_type == "json" and body:
            try:
                r = req_lib.request(method, url, headers={**req_headers, "Content-Type": "application/json"},
                                     json=json.loads(body), timeout=30)
            except json.JSONDecodeError:
                r = req_lib.request(method, url, headers=req_headers, data=body, timeout=30)
        else:
            r = req_lib.request(method, url, headers=req_headers, data=body, timeout=30)

        elapsed = time.time() - start

        response_body = r.text[:50000]
        return jsonify({
            "status": "ok",
            "status_code": r.status_code,
            "status_text": f"{r.status_code} {r.reason}",
            "headers": dict(r.headers),
            "body": response_body,
            "body_size": len(r.text),
            "elapsed": round(elapsed, 3),
        })

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})


# ─── SYSTEM STATS EXTENDED ───────────────────
@app.route("/api/system/extended")
@login_required
def api_system_extended():
    stats = get_system_stats()
    stats["docker"] = docker_mgr.available
    stats["plugins"] = len(plugin_loader.list_plugins())
    try:
        net = psutil.net_io_counters()
        stats["network_io"] = {
            "bytes_sent_per_sec": 0,
            "bytes_recv_per_sec": 0,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errin": net.errin,
            "errout": net.errout,
        }
    except Exception:
        pass
    return jsonify(stats)


# ─── SYSTEM SEARCH (global) ──────────────────
@app.route("/api/search", methods=["POST"])
@login_required
def api_global_search():
    data = request.json or {}
    query = data.get("q", "").lower()
    if not query:
        return jsonify({"error": "Query required"}), 400

    results = {"files": [], "agents": [], "apps": [], "settings": []}

    # Search files
    for root, dirs, files in os.walk(STORAGE_DIR):
        for f in files:
            if query in f.lower():
                fpath = os.path.join(root, f)
                results["files"].append({"name": f, "path": fpath, "type": "file"})
                if len(results["files"]) >= 20:
                    break
        if len(results["files"]) >= 20:
            break

    # Search agents
    for agent in hub.list_agents():
        if query in agent["name"].lower() or query in agent["description"].lower():
            results["agents"].append({"name": agent["name"], "description": agent["description"]})

    return jsonify(results)


# ══════════════════════════════════════════════
#  NEW ADVANCED FEATURES
# ══════════════════════════════════════════════

# ─── FILE COMPRESSION ─────────────────────
@app.route("/api/files/zip", methods=["POST"])
@login_required
def api_files_zip():
    data = request.json or {}
    src = data.get("src", "")
    dst = data.get("dst", "")
    full_src = resolve_path(src)
    full_dst = resolve_path(dst) if dst else full_src + ".zip"
    try:
        with zipfile.ZipFile(full_dst, 'w', zipfile.ZIP_DEFLATED) as zf:
            if os.path.isfile(full_src):
                zf.write(full_src, os.path.basename(full_src))
            else:
                for root, dirs, files in os.walk(full_src):
                    for f in files:
                        fp = os.path.join(root, f)
                        zf.write(fp, os.path.relpath(fp, os.path.dirname(full_src)))
        return jsonify({"status": "ok", "path": full_dst, "size": os.path.getsize(full_dst)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/unzip", methods=["POST"])
@login_required
def api_files_unzip():
    data = request.json or {}
    src = data.get("src", "")
    dst = data.get("dst", "")
    full_src = resolve_path(src)
    full_dst = resolve_path(dst) if dst else full_src.rsplit(".", 1)[0]
    try:
        os.makedirs(full_dst, exist_ok=True)
        with zipfile.ZipFile(full_src, 'r') as zf:
            zf.extractall(full_dst)
        return jsonify({"status": "ok", "extracted_to": full_dst})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/tar", methods=["POST"])
@login_required
def api_files_tar():
    data = request.json or {}
    src = data.get("src", "")
    dst = data.get("dst", "")
    full_src = resolve_path(src)
    full_dst = resolve_path(dst) if dst else full_src + ".tar.gz"
    try:
        with tarfile.open(full_dst, 'w:gz') as tf:
            tf.add(full_src, os.path.basename(full_src))
        return jsonify({"status": "ok", "path": full_dst})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/untar", methods=["POST"])
@login_required
def api_files_untar():
    data = request.json or {}
    src = data.get("src", "")
    dst = data.get("dst", "")
    full_src = resolve_path(src)
    full_dst = resolve_path(dst) if dst else full_src.rsplit(".", 1)[0]
    try:
        os.makedirs(full_dst, exist_ok=True)
        with tarfile.open(full_src, 'r') as tf:
            tf.extractall(full_dst)
        return jsonify({"status": "ok", "extracted_to": full_dst})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── FILE ENCRYPTION ─────────────────────
@app.route("/api/files/encrypt", methods=["POST"])
@login_required
def api_files_encrypt():
    data = request.json or {}
    src = data.get("src", "")
    password = data.get("password", "webos")
    full_src = resolve_path(src)
    if not os.path.isfile(full_src):
        return jsonify({"error": "File not found"}), 404
    try:
        with open(full_src, 'rb') as f:
            plain = f.read()
        key = hashlib.sha256(password.encode()).digest()
        from cryptography.fernet import Fernet
        fkey = base64.urlsafe_b64encode(key)
        cipher = Fernet(fkey)
        encrypted = cipher.encrypt(plain)
        dst = full_src + ".enc"
        with open(dst, 'wb') as f:
            f.write(encrypted)
        return jsonify({"status": "ok", "path": dst, "size": len(encrypted)})
    except ImportError:
        return jsonify({"error": "cryptography library not installed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/decrypt", methods=["POST"])
@login_required
def api_files_decrypt():
    data = request.json or {}
    src = data.get("src", "")
    password = data.get("password", "webos")
    full_src = resolve_path(src)
    if not os.path.isfile(full_src):
        return jsonify({"error": "File not found"}), 404
    try:
        with open(full_src, 'rb') as f:
            encrypted = f.read()
        key = hashlib.sha256(password.encode()).digest()
        from cryptography.fernet import Fernet
        fkey = base64.urlsafe_b64encode(key)
        cipher = Fernet(fkey)
        plain = cipher.decrypt(encrypted)
        dst = full_src.replace(".enc", ".decrypted") if full_src.endswith(".enc") else full_src + ".decrypted"
        with open(dst, 'wb') as f:
            f.write(plain)
        return jsonify({"status": "ok", "path": dst, "size": len(plain)})
    except ImportError:
        return jsonify({"error": "cryptography library not installed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── ACTIVITY LOG ─────────────────────────
@app.route("/api/activity/log", methods=["POST"])
@login_required
def api_activity_log():
    data = request.json or {}
    action = data.get("action", "")
    detail = data.get("detail", "")
    if action:
        db.execute("INSERT INTO notifications (title, message, type, read) VALUES (?, ?, ?, 1)",
                    (action, detail, "info"))
    return jsonify({"status": "ok"})

@app.route("/api/activity/list")
@login_required
def api_activity_list():
    rows = db.query("SELECT id, title, message, type, created_at FROM notifications ORDER BY created_at DESC LIMIT 100")
    return jsonify({"activities": [{
        "id": r["id"], "action": r["title"], "detail": r["message"],
        "type": r["type"], "time": r["created_at"]
    } for r in rows]})

# ─── PORT SCANNER ─────────────────────────
@app.route("/api/network/scan", methods=["POST"])
@login_required
def api_port_scan():
    data = request.json or {}
    host = data.get("host", "127.0.0.1")
    ports = data.get("ports", "1-1024")
    timeout = data.get("timeout", 1.0)
    results = []
    try:
        parts = ports.split("-")
        start_p = int(parts[0])
        end_p = int(parts[1]) if len(parts) > 1 else start_p
        for port in range(start_p, min(end_p + 1, 65536)):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            if result == 0:
                try:
                    service = socket.getservbyport(port)
                except:
                    service = "unknown"
                results.append({"port": port, "service": service, "state": "open"})
            sock.close()
        return jsonify({"host": host, "open_ports": results, "count": len(results)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── DOWNLOAD MANAGER ─────────────────────
download_tasks = {}
download_counter = 0

@app.route("/api/download/start", methods=["POST"])
@login_required
def api_download_start():
    global download_counter
    data = request.json or {}
    url = data.get("url", "")
    filename = data.get("filename", "")
    if not url:
        return jsonify({"error": "URL required"}), 400
    import requests
    download_counter += 1
    task_id = f"dl_{download_counter}"
    if not filename:
        filename = url.split("/")[-1] or f"download_{task_id}"
    dest = os.path.join(STORAGE_DIR, "downloads", filename)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    def dl_worker():
        try:
            r = requests.get(url, stream=True, timeout=60)
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            download_tasks[task_id] = {"id": task_id, "url": url, "filename": filename, "total": total, "downloaded": 0, "status": "downloading", "dest": dest}
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if task_id in download_tasks:
                            download_tasks[task_id]["downloaded"] = downloaded
            if task_id in download_tasks:
                download_tasks[task_id]["status"] = "completed"
                WebSocketServer.notify("Download Complete", filename, "success")
        except Exception as e:
            if task_id in download_tasks:
                download_tasks[task_id]["status"] = "error"
                download_tasks[task_id]["error"] = str(e)
    download_tasks[task_id] = {"id": task_id, "url": url, "filename": filename, "total": 0, "downloaded": 0, "status": "queued", "dest": dest}
    threading.Thread(target=dl_worker, daemon=True).start()
    return jsonify({"task_id": task_id, "status": "queued"})

@app.route("/api/download/list")
@login_required
def api_download_list():
    return jsonify({"tasks": list(download_tasks.values())})

@app.route("/api/download/cancel", methods=["POST"])
@login_required
def api_download_cancel():
    data = request.json or {}
    task_id = data.get("task_id", "")
    if task_id in download_tasks:
        download_tasks[task_id]["status"] = "cancelled"
        return jsonify({"status": "cancelled"})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/download/clear", methods=["POST"])
@login_required
def api_download_clear():
    global download_tasks
    download_tasks = {k: v for k, v in download_tasks.items() if v["status"] == "downloading"}
    return jsonify({"status": "ok"})

# ─── MEDIA INFO ───────────────────────────
@app.route("/api/media/info", methods=["POST"])
@login_required
def api_media_info():
    data = request.json or {}
    path = data.get("path", "")
    full = resolve_path(path)
    if not os.path.isfile(full):
        return jsonify({"error": "File not found"}), 404
    mime, _ = mimetypes.guess_type(full)
    stat = os.stat(full)
    info = {
        "name": os.path.basename(full),
        "path": full,
        "size": stat.st_size,
        "mime": mime or "application/octet-stream",
        "modified": stat.st_mtime,
    }
    if mime and mime.startswith("image/"):
        try:
            from PIL import Image
            img = Image.open(full)
            info["width"], info["height"] = img.size
            info["format"] = img.format
        except ImportError:
            pass
    elif mime and mime.startswith("audio/"):
        try:
            import mutagen
            from mutagen.mp3 import MP3
            if mime == "audio/mpeg":
                audio = MP3(full)
                info["duration"] = audio.info.length
                info["bitrate"] = audio.info.bitrate
                info["sample_rate"] = audio.info.sample_rate
        except ImportError:
            pass
    elif mime and mime.startswith("video/"):
        try:
            import subprocess as sp
            result = sp.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", full],
                          capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                probe = json.loads(result.stdout)
                info["streams"] = [{"codec": s.get("codec_name"), "type": s.get("codec_type"),
                                    "width": s.get("width"), "height": s.get("height")} for s in probe.get("streams", [])]
                if probe.get("format"):
                    info["duration"] = float(probe["format"].get("duration", 0))
                    info["bitrate"] = probe["format"].get("bit_rate")
        except Exception:
            pass
    return jsonify(info)


# ─── WHITEBOARD ───────────────────────────
whiteboard_data = {"strokes": [], "bg": "#0a0a1a"}

@app.route("/api/whiteboard/save", methods=["POST"])
@login_required
def api_whiteboard_save():
    global whiteboard_data
    data = request.json or {}
    whiteboard_data = {"strokes": data.get("strokes", []), "bg": data.get("bg", "#0a0a1a")}
    return jsonify({"status": "ok"})

@app.route("/api/whiteboard/load")
@login_required
def api_whiteboard_load():
    return jsonify(whiteboard_data)

# ─── TODO LIST ────────────────────────────
@app.route("/api/todos/list")
@login_required
def api_todos_list():
    rows = db.query("SELECT * FROM todos ORDER BY created_at DESC")
    return jsonify({"todos": [{
        "id": r["id"], "title": r.get("title", ""), "description": r.get("description", ""),
        "status": r.get("status", "pending"), "priority": r.get("priority", "medium"),
        "created_at": r["created_at"]
    } for r in rows]})

@app.route("/api/todos/create", methods=["POST"])
@login_required
def api_todos_create():
    data = request.json or {}
    title = data.get("title", "")
    desc = data.get("description", "")
    priority = data.get("priority", "medium")
    type_val = data.get("type", "todo")
    if not title:
        return jsonify({"error": "Title required"}), 400
    db.execute("INSERT INTO todos (title, description, status, priority, type) VALUES (?, ?, 'pending', ?, ?)",
               (title, desc, priority, type_val))
    return jsonify({"status": "ok", "id": db.last_id()})

@app.route("/api/todos/update", methods=["POST"])
@login_required
def api_todos_update():
    data = request.json or {}
    tid = data.get("id")
    status = data.get("status")
    if tid and status:
        db.execute("UPDATE todos SET status = ? WHERE id = ?", (status, tid))
        return jsonify({"status": "ok"})
    return jsonify({"error": "id and status required"}), 400

@app.route("/api/todos/delete", methods=["POST"])
@login_required
def api_todos_delete():
    data = request.json or {}
    tid = data.get("id")
    if tid:
        db.execute("DELETE FROM todos WHERE id = ?", (tid,))
        return jsonify({"status": "ok"})
    return jsonify({"error": "id required"}), 400

# ─── KANBAN ───────────────────────────────
@app.route("/api/kanban/boards")
@login_required
def api_kanban_boards():
    rows = db.query("SELECT * FROM todos WHERE type='kanban' ORDER BY created_at")
    boards = {}
    for r in rows:
        col = r.get("status", "backlog")
        if col not in boards:
            boards[col] = []
        boards[col].append({"id": r["id"], "title": r.get("title", ""), "description": r.get("description", "")})
    if not boards:
        boards = {"backlog": [], "todo": [], "in_progress": [], "done": []}
    return jsonify({"boards": boards})

@app.route("/api/kanban/move", methods=["POST"])
@login_required
def api_kanban_move():
    data = request.json or {}
    tid = data.get("id")
    status = data.get("status", "backlog")
    if tid:
        db.execute("UPDATE todos SET status = ?, type = 'kanban' WHERE id = ?", (status, tid))
        return jsonify({"status": "ok"})
    return jsonify({"error": "id required"}), 400

# ─── ACTIVITY LOG DB INIT ─────────────────
try:
    db.execute("CREATE TABLE IF NOT EXISTS activity_log (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, detail TEXT, type TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
except Exception:
    pass


# ══════════════════════════════════════════════
#  NEW ADVANCED API ENDPOINTS v6.0
# ══════════════════════════════════════════════


# ─── AGENT CONVERSATION CHAIN ──────────
@app.route("/api/agents/chain", methods=["POST"])
@login_required
def api_agents_chain():
    data = request.json or {}
    message = data.get("message", "")
    agents_order = data.get("agents", [])  # Optional: specify order
    if not message:
        return jsonify({"error": "Message required"}), 400
    results = {}
    if agents_order:
        for agent_name in agents_order:
            r = hub.run_agent(agent_name, message)
            results[agent_name] = r.get("result", r.get("error", "unknown"))
    else:
        for name in hub.agents:
            try:
                r = hub.run_agent(name, message)
                results[name] = r.get("result", str(r)[:500])
            except Exception as e:
                results[name] = f"Error: {e}"
    return jsonify({"chain_results": results})


@app.route("/api/agents/conversation")
@login_required
def api_agents_conversation():
    return jsonify({"conversation": hub.conversation[-50:]})


@app.route("/api/agents/clear", methods=["POST"])
@login_required
def api_agents_clear():
    hub.conversation = []
    return jsonify({"status": "ok"})


# ─── SYSTEM UPDATE CHECK ───────────────
@app.route("/api/system/updates")
@login_required
def api_system_updates():
    try:
        result = subprocess.run(
            ["pip", "list", "--outdated", "--format=columns"],
            capture_output=True, text=True, timeout=30
        )
        lines = [l for l in result.stdout.split("\n") if l.strip()][2:]
        updates = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                updates.append({"package": parts[0], "current": parts[1], "latest": parts[2]})
        return jsonify({"updates": updates, "count": len(updates)})
    except Exception as e:
        return jsonify({"error": str(e), "updates": [], "count": 0})


# ─── PACKAGE MANAGER ──────────────────
@app.route("/api/system/package/install", methods=["POST"])
@login_required
def api_package_install():
    data = request.json or {}
    pkg = data.get("package", "")
    if not pkg:
        return jsonify({"error": "Package name required"}), 400
    try:
        result = subprocess.run(
            ["pip", "install", pkg],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            db.add_notification("Package Installed", pkg, "success")
            return jsonify({"status": "ok", "output": result.stdout[-500:]})
        return jsonify({"status": "error", "output": result.stderr[-500:]}), 400
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "output": "Installation timed out"}), 408
    except Exception as e:
        return jsonify({"status": "error", "output": str(e)}), 500


@app.route("/api/system/package/uninstall", methods=["POST"])
@login_required
def api_package_uninstall():
    data = request.json or {}
    pkg = data.get("package", "")
    if not pkg:
        return jsonify({"error": "Package name required"}), 400
    try:
        result = subprocess.run(
            ["pip", "uninstall", "-y", pkg],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return jsonify({"status": "ok", "output": result.stdout[-300:]})
        return jsonify({"status": "error", "output": result.stderr[-300:]}), 400
    except Exception as e:
        return jsonify({"status": "error", "output": str(e)}), 500


@app.route("/api/system/package/list")
@login_required
def api_package_list():
    try:
        result = subprocess.run(
            ["pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=30
        )
        packages = json.loads(result.stdout) if result.stdout else []
        return jsonify({"packages": packages, "count": len(packages)})
    except Exception as e:
        return jsonify({"error": str(e), "packages": [], "count": 0})


# ─── SYSTEM LOGS ──────────────────────
@app.route("/api/system/logs")
@login_required
def api_system_logs():
    service = request.args.get("service", "webos")
    lines = request.args.get("lines", 50, type=int)
    try:
        result = subprocess.run(
            ["journalctl", "-u", service, "--no-pager", "-n", str(lines)],
            capture_output=True, text=True, timeout=10
        )
        log_lines = result.stdout.split("\n") if result.stdout else ["No logs available"]
        return jsonify({"service": service, "logs": log_lines, "count": len(log_lines)})
    except Exception:
        return jsonify({"service": service, "logs": ["journalctl not available (running on Windows or no systemd)"], "count": 0})


# ─── NETWORK SPEED TEST ───────────────
@app.route("/api/network/speed")
@login_required
def api_network_speed():
    import time
    try:
        start = time.time()
        result = subprocess.run(["ping", "-n", "4", "8.8.8.8"] if os.name == "nt"
                                else ["ping", "-c", "4", "8.8.8.8"],
                                capture_output=True, text=True, timeout=20)
        elapsed = time.time() - start
        lines = result.stdout.split("\n")
        stats = [l.strip() for l in lines if "time" in l.lower() or "ttl" in l.lower() or "avg" in l.lower() or "rtt" in l.lower()]
        return jsonify({"ping": "OK", "elapsed": round(elapsed, 2), "stats": stats[:3] if stats else ["No data"]})
    except Exception:
        return jsonify({"ping": "FAIL", "elapsed": 0, "stats": ["Ping failed"]})


# ─── SYSTEM SENSORS ───────────────────
@app.route("/api/system/sensors")
@login_required
def api_system_sensors():
    sensors = {}
    try:
        temps = psutil.sensors_temperatures()
        for name, entries in temps.items():
            sensors[name] = [{"label": e.label or name, "current": e.current, "high": e.high, "critical": e.critical}
                             for e in entries]
    except Exception:
        sensors["error"] = "Temperature sensors not available"
    try:
        fans = psutil.sensors_fans()
        for name, entries in fans.items():
            if "fans" not in sensors:
                sensors["fans"] = {}
            sensors["fans"][name] = [{"label": e.label or name, "rpm": e.current} for e in entries]
    except Exception:
        pass
    return jsonify(sensors)


# ─── HARDWARE INFO ────────────────────
@app.route("/api/system/hardware")
@login_required
def api_system_hardware():
    info = {"cpu": {}, "memory": {}, "disks": [], "network": {}}
    info["cpu"]["brand"] = platform.processor() or "Unknown"
    info["cpu"]["arch"] = platform.machine()
    info["cpu"]["cores"] = psutil.cpu_count(logical=False)
    info["cpu"]["threads"] = psutil.cpu_count(logical=True)
    mem = psutil.virtual_memory()
    info["memory"]["total"] = mem.total
    info["memory"]["type"] = "DDR4" if mem.total > 8e9 else "DDR3"
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            info["disks"].append({
                "device": part.device, "mount": part.mountpoint,
                "fstype": part.fstype, "total": usage.total,
            })
        except Exception:
            pass
    try:
        net_addrs = psutil.net_if_addrs()
        for name, addrs in net_addrs.items():
            for a in addrs:
                if a.family == 2:  # AF_INET
                    info["network"][name] = {"ip": a.address, "netmask": a.netmask}
    except Exception:
        pass
    return jsonify(info)


# ─── DISK USAGE VISUAL ────────────────
@app.route("/api/system/disk/analyze")
@login_required
def api_disk_analyze():
    path = request.args.get("path", "/")
    result = {"path": path, "total": 0, "items": []}
    try:
        if os.path.isfile(path):
            return jsonify({"error": "Path is a file"}), 400
        total_size = 0
        items = []
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file():
                        sz = entry.stat().st_size
                        items.append({"name": entry.name, "size": sz, "type": "file"})
                        total_size += sz
                    elif entry.is_dir():
                        sz = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fn in os.walk(entry.path) for f in fn if os.path.isfile(os.path.join(dp, f))) if os.path.exists(entry.path) else 0
                        items.append({"name": entry.name, "size": sz, "type": "dir"})
                        total_size += sz
                except Exception:
                    pass
        items.sort(key=lambda x: -x["size"])
        result["total"] = total_size
        result["items"] = items[:100]
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(result)


# ─── SYSTEM LOCATION ──────────────────
@app.route("/api/system/location")
@login_required
def api_system_location():
    try:
        import requests as req
        r = req.get("http://ip-api.com/json/", timeout=5)
        return jsonify(r.json())
    except Exception:
        return jsonify({"error": "Could not determine location", "city": "Unknown", "country": "Unknown"})


# ─── DISPLAY INFO ─────────────────────
@app.route("/api/system/display")
@login_required
def api_system_display():
    info = {
        "resolutions": [],
        "current": {"width": 1920, "height": 1080},
        "connected": True,
    }
    try:
        result = subprocess.run(["xrandr", "--current"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split("\n"):
            if "connected" in line:
                m = re.search(r'(\d+)x(\d+)', line)
                if m:
                    info["resolutions"].append({"mode": m.group(0), "width": int(m.group(1)), "height": int(m.group(2))})
    except Exception:
        info["detected"] = "X11 not available (running headless)"
    return jsonify(info)


# ─── MULTI-AGENT CHAT ─────────────────
@app.route("/api/agents/chat", methods=["POST"])
@login_required
def api_multi_agent_chat():
    data = request.json or {}
    message = data.get("message", "")
    mode = data.get("mode", "auto")  # auto, broadcast, chain, plan
    if not message:
        return jsonify({"error": "Message required"}), 400
    if mode == "broadcast":
        results = hub.broadcast(message)
        return jsonify({"mode": "broadcast", "results": results})
    elif mode == "plan":
        plan = hub.create_plan(message)
        results = {}
        for step in plan["steps"]:
            r = hub.run_agent(step["agent"], step["task"])
            results[step["agent"]] = r.get("result", r.get("error", ""))
        return jsonify({"mode": "plan", "plan": plan, "results": results})
    elif mode == "chain":
        results = {}
        for name in hub.agents:
            try:
                r = hub.run_agent(name, message)
                results[name] = r.get("result", str(r)[:500])
            except Exception as e:
                results[name] = f"Error: {e}"
        return jsonify({"mode": "chain", "results": results})
    else:
        result = hub.process_message(message)
        return jsonify({"mode": "auto", "result": result})


# ─── SYSTEMCTL COMMANDS ───────────────
@app.route("/api/system/service/<action>", methods=["POST"])
@login_required
def api_system_service(action):
    data = request.json or {}
    service = data.get("service", "webos")
    if action not in ("start", "stop", "restart", "status", "enable", "disable"):
        return jsonify({"error": "Invalid action"}), 400
    try:
        result = subprocess.run(
            ["systemctl", action, service],
            capture_output=True, text=True, timeout=30
        )
        return jsonify({
            "action": action, "service": service,
            "returncode": result.returncode,
            "stdout": result.stdout[:300] if result.stdout else "",
            "stderr": result.stderr[:300] if result.stderr else "",
        })
    except FileNotFoundError:
        return jsonify({"action": action, "service": service, "error": "systemctl not available (not Linux/systemd)"})
    except Exception as e:
        return jsonify({"action": action, "service": service, "error": str(e)})


# ─── WEB OS VERSION INFO ──────────────
@app.route("/api/system/version")
@login_required
def api_system_version():
    return jsonify({
        "version": "1.0",
        "name": "Web OS",
        "edition": "Complete",
        "agents": len(hub.list_agents()),
        "arch": platform.machine(),
        "uptime": time.time() - psutil.boot_time() if hasattr(psutil, "boot_time") else 0,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
    })


# ─── SUB-AGENT SYSTEM (600+ agents) ────
from agents.agent_sub_agents import SubAgentSystem
_sub_agents = SubAgentSystem()

@app.route("/api/subagents/process", methods=["POST"])
@login_required
def api_subagents_process():
    data = request.json or {}
    message = data.get("message", "")
    main_agent = data.get("main_agent")
    sub_agent_id = data.get("sub_agent_id")
    if not message:
        return jsonify({"error": "No message"}), 400
    result = _sub_agents.process(message, main_agent, sub_agent_id)
    return jsonify(result)

@app.route("/api/subagents/list/<main_agent>")
@login_required
def api_subagents_list(main_agent):
    agents = _sub_agents.list_by_main(main_agent)
    return jsonify({"main_agent": main_agent, "count": len(agents), "sub_agents": agents})

@app.route("/api/subagents/stats")
@login_required
def api_subagents_stats():
    return jsonify(_sub_agents.get_stats())

@app.route("/api/subagents/search", methods=["POST"])
@login_required
def api_subagents_search():
    data = request.json or {}
    query = data.get("query", "").lower()
    results = []
    for sa_id, sa in _sub_agents.sub_agents.items():
        if query in sa_id.lower() or query in sa["role"].lower() or query in sa["department"].lower():
            results.append(sa)
        if len(results) >= 50:
            break
    return jsonify({"query": query, "count": len(results), "results": results})


# ─── REAL OS FEATURES ──────────────────
@app.route("/api/os/processes")
@login_required
def api_os_processes():
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status", "username", "create_time"]):
            try:
                info = p.info
                info["cpu"] = info.pop("cpu_percent", 0)
                info["mem"] = round(info.pop("memory_percent", 0), 1)
                info["time"] = int(info.pop("create_time", 0))
                procs.append(info)
            except Exception:
                pass
        procs.sort(key=lambda x: -x.get("mem", 0))
        return jsonify({"total": len(procs), "processes": procs[:100]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/os/process/kill", methods=["POST"])
@login_required
def api_os_process_kill():
    data = request.json or {}
    pid = data.get("pid")
    if not pid:
        return jsonify({"error": "No PID"}), 400
    try:
        import os, signal
        os.kill(int(pid), signal.SIGKILL)
        return jsonify({"ok": True, "pid": pid})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/os/users")
@login_required
def api_os_users():
    try:
        import pwd
        users = []
        for u in pwd.getpwall():
            users.append({"name": u.pw_name, "uid": u.pw_uid, "gid": u.pw_gid, "home": u.pw_dir, "shell": u.pw_shell})
        return jsonify({"total": len(users), "users": users})
    except Exception:
        import os
        users = []
        try:
            with open("/etc/passwd") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) >= 7:
                        users.append({"name": parts[0], "uid": parts[2], "gid": parts[3], "home": parts[5], "shell": parts[6]})
        except Exception:
            pass
        return jsonify({"total": len(users), "users": users[:50]})

@app.route("/api/os/groups")
@login_required
def api_os_groups():
    groups = []
    try:
        with open("/etc/group") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 3:
                    groups.append({"name": parts[0], "gid": parts[2], "members": parts[3].split(",") if parts[3] else []})
        return jsonify({"total": len(groups), "groups": groups})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/os/services")
@login_required
def api_os_services():
    try:
        import subprocess
        result = subprocess.run(["systemctl", "list-units", "--type=service", "--no-pager", "--no-legend"], capture_output=True, text=True, timeout=10)
        services = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 4:
                services.append({"name": parts[0], "load": parts[1], "active": parts[2], "sub": parts[3], "description": " ".join(parts[4:])})
        return jsonify({"total": len(services), "services": services[:100]})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/os/disks")
@login_required
def api_os_disks():
    try:
        import psutil
        disks = []
        for p in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({"device": p.device, "mount": p.mountpoint, "fstype": p.fstype, "total": usage.total, "used": usage.used, "free": usage.free, "percent": usage.percent})
            except Exception:
                disks.append({"device": p.device, "mount": p.mountpoint, "fstype": p.fstype})
        return jsonify({"total": len(disks), "disks": disks})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/os/memory")
@login_required
def api_os_memory():
    try:
        import psutil
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return jsonify({
            "memory": {"total": mem.total, "available": mem.available, "used": mem.used, "percent": mem.percent, "free": mem.free},
            "swap": {"total": swap.total, "used": swap.used, "free": swap.free, "percent": swap.percent}
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/os/environment")
@login_required
def api_os_environment():
    env = dict(os.environ)
    safe_env = {k: v for k, v in env.items() if not any(secret in k.lower() for secret in ["key", "secret", "pass", "token", "auth"])}
    return jsonify({"total": len(safe_env), "variables": safe_env})

@app.route("/api/os/uptime")
@login_required
def api_os_uptime():
    try:
        import psutil
        boot = psutil.boot_time()
        uptime_seconds = time.time() - boot
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return jsonify({
            "uptime_seconds": int(uptime_seconds), "days": days, "hours": hours, "minutes": minutes,
            "boot_time": datetime.fromtimestamp(boot).isoformat(),
            "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0, 0, 0]
        })
    except Exception as e:
        return jsonify({"error": str(e)})


# ─── MULTI-AGENT ADVANCED CHAT ────────
@app.route("/api/agents/smart", methods=["POST"])
@login_required
def api_agents_smart():
    data = request.json or {}
    message = data.get("message", "")
    mode = data.get("mode", "auto")
    session_id = data.get("session_id", "default")
    if not message:
        return jsonify({"error": "No message"}), 400
    result = hub.process_message(message, mode, session_id)
    return jsonify(result)


@app.route("/api/agents/status")
@login_required
def api_agents_status():
    return jsonify(hub.get_status())


@app.route("/api/agents/memory/<agent_name>", methods=["GET", "POST"])
@login_required
def api_agents_memory(agent_name):
    from agents.agent_memory import AgentMemory
    mem = AgentMemory(agent_name)
    if request.method == "POST":
        data = request.json or {}
        action = data.get("action", "")
        if action == "save_fact":
            mem.save_fact(data["fact"], source="user", confidence=data.get("confidence", 1.0))
            return jsonify({"ok": True})
        if action == "set_pref":
            mem.set_preference(data["key"], data["value"])
            return jsonify({"ok": True})
        return jsonify({"error": "Unknown action"}), 400
    topic = request.args.get("topic")
    return jsonify({"agent": agent_name, "stats": mem.get_stats(), "facts": mem.get_facts(topic)})


@app.route("/api/agents/orchestrator/analyze", methods=["POST"])
@login_required
def api_orchestrator_analyze():
    data = request.json or {}
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "No query"}), 400
    analysis = hub.orchestrator.analyze_query(query)
    route = hub.orchestrator.route(query, data.get("mode", "auto"), data.get("session_id"))
    return jsonify({"analysis": analysis, "route": route})


# ─── DESKTOP SETTINGS ─────────────────
@app.route("/api/desktop/settings", methods=["GET", "POST"])
@login_required
def api_desktop_settings():
    from agents.agent_memory import AgentMemory
    mem = AgentMemory("desktop")
    if request.method == "POST":
        data = request.json or {}
        for k, v in data.items():
            mem.set_preference(k, v)
        return jsonify({"ok": True})
    settings = {}
    for key in ["wallpaper", "theme", "accent_color", "taskbar_pos", "font_size", "language"]:
        val = mem.get_preference(key)
        if val is not None:
            settings[key] = val
    return jsonify(settings)


@app.route("/api/desktop/tasks")
@login_required
def api_desktop_tasks():
    return jsonify(hub.list_tasks())


@app.route("/api/desktop/stats")
@login_required
def api_desktop_stats():
    try:
        cpu = psutil.cpu_percent(interval=0.05)
        mem = psutil.virtual_memory()
        d = psutil.disk_usage("/")
        return jsonify({
            "cpu": cpu, "cpu_count": psutil.cpu_count(),
            "memory": {"total": mem.total, "used": mem.used, "percent": mem.percent},
            "disk": {"total": d.total, "used": d.used, "percent": d.percent, "free": d.free},
            "uptime": int(time.time() - psutil.boot_time()),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── NOTIFICATION SYSTEM ──────────────
_notifications = []
_notif_lock = threading.Lock()

@app.route("/api/notifications", methods=["GET", "POST", "DELETE"])
@login_required
def api_live_notifications():
    global _notifications
    if request.method == "POST":
        data = request.json or {}
        notif = {
            "id": str(uuid.uuid4())[:8],
            "title": data.get("title", "Notification"),
            "message": data.get("message", ""),
            "icon": data.get("icon", "info"),
            "time": datetime.now().isoformat(),
            "read": False
        }
        with _notif_lock:
            _notifications.insert(0, notif)
            if len(_notifications) > 50:
                _notifications = _notifications[:50]
        return jsonify(notif)
    if request.method == "DELETE":
        notif_id = request.args.get("id")
        with _notif_lock:
            if notif_id:
                _notifications = [n for n in _notifications if n["id"] != notif_id]
            else:
                _notifications = []
        return jsonify({"ok": True})
    return jsonify(_notifications)


# ─── AGENT COMPANY (50-AGENT ENTERPRISE) ─
from agents.agent_company import AgentCompany
_agent_company = AgentCompany()

@app.route("/api/company/process", methods=["POST"])
@login_required
def api_company_process():
    data = request.json or {}
    message = data.get("message", "")
    mode = data.get("mode", "auto")
    if not message:
        return jsonify({"error": "No message"}), 400
    result = _agent_company.process(message, mode)
    return jsonify(result)

@app.route("/api/company/org")
@login_required
def api_company_org():
    return jsonify(_agent_company.get_org_chart())

@app.route("/api/company/stats")
@login_required
def api_company_stats():
    return jsonify(_agent_company.get_stats())

# ─── DOCUMENT PROCESSOR ────────────────
from server.extensions.document_processor import DocumentProcessor
_doc_proc = DocumentProcessor(STORAGE_DIR)

@app.route("/api/documents/read", methods=["POST"])
@login_required
def api_documents_read():
    data = request.json or {}
    path = data.get("path", "")
    if not path:
        return jsonify({"error": "No path"}), 400
    result = _doc_proc.read(path)
    return jsonify(result)

@app.route("/api/documents/list", methods=["POST"])
@login_required
def api_documents_list():
    data = request.json or {}
    dir_path = data.get("path", STORAGE_DIR)
    result = _doc_proc.ls(dir_path)
    return jsonify(result)

@app.route("/api/documents/search", methods=["POST"])
@login_required
def api_documents_search():
    data = request.json or {}
    query = data.get("query", "")
    root = data.get("path", STORAGE_DIR)
    if not query:
        return jsonify({"error": "No query"}), 400
    result = _doc_proc.search(root, query)
    return jsonify(result)

@app.route("/api/documents/preview", methods=["POST"])
@login_required
def api_documents_preview():
    data = request.json or {}
    path = data.get("path", "")
    if not path:
        return jsonify({"error": "No path"}), 400
    result = _doc_proc.preview(path)
    return jsonify(result)

# ─── MEDIA STREAMING ───────────────────
@app.route("/api/media/stream/<path:filepath>")
@login_required
def api_media_stream(filepath):
    fp = resolve_path(filepath)
    if not os.path.exists(fp):
        return jsonify({"error": "File not found"}), 404
    range_header = request.headers.get("Range", None)
    file_size = os.path.getsize(fp)
    if range_header:
        start, end = 0, file_size - 1
        range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start = int(range_match.group(1))
            if range_match.group(2):
                end = int(range_match.group(2))
        if start >= file_size:
            return "", 416
        chunk_size = min(end - start + 1, 1048576)
        with open(fp, "rb") as f:
            f.seek(start)
            data = f.read(chunk_size)
        resp = app.response_class(data, 206, mimetype=mimetypes.guess_type(fp)[0] or "application/octet-stream")
        resp.headers.add("Content-Range", f"bytes {start}-{start+len(data)-1}/{file_size}")
        resp.headers.add("Accept-Ranges", "bytes")
        resp.headers.add("Content-Length", str(len(data)))
        return resp
    return send_file(fp, mimetype=mimetypes.guess_type(fp)[0] or "application/octet-stream")


def start(host="0.0.0.0", port=8080, debug=False):
    print(f"[HTTP] Server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)
