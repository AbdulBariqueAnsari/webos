import os, json, socket, threading, time, subprocess
from datetime import datetime

DEVICES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "devices.json")


class DeviceManager:
    def __init__(self):
        self.devices = self._load()
        self.lock = threading.Lock()

    def _load(self):
        if os.path.exists(DEVICES_FILE):
            try:
                with open(DEVICES_FILE) as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        os.makedirs(os.path.dirname(DEVICES_FILE), exist_ok=True)
        with open(DEVICES_FILE, "w") as f:
            json.dump(self.devices, f, indent=2)

    def list_devices(self):
        return self.devices

    def scan_network(self):
        local_ip = self._local_ip()
        if not local_ip:
            return []
        base = ".".join(local_ip.split(".")[:-1])
        found = []
        threads = []

        def probe(ip):
            results = []
            for port, ptype in [(22, "ssh_device"), (80, "http_device"), (443, "https_device"),
                                 (8080, "webos_device"), (445, "smb_device"), (21, "ftp_device")]:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.3)
                    if s.connect_ex((ip, port)) == 0:
                        results.append((port, ptype))
                    s.close()
                except Exception:
                    pass
            if results:
                ports = [r[0] for r in results]
                dtype = results[0][1]
                try:
                    hostname, _, _ = socket.gethostbyaddr(ip)
                except Exception:
                    hostname = "Unknown"
                with self.lock:
                    dev = {"ip": ip, "hostname": hostname, "ports": ports, "type": dtype,
                           "last_seen": datetime.now().isoformat()}
                    self._upsert(dev)
                    found.append(dev)

        for i in range(1, 255):
            t = threading.Thread(target=probe, args=(f"{base}.{i}",), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=3)
        self._save()
        return found

    def _upsert(self, dev):
        for i, d in enumerate(self.devices):
            if d["ip"] == dev["ip"]:
                dev["first_seen"] = d.get("first_seen", dev["last_seen"])
                self.devices[i] = dev
                return
        dev["first_seen"] = dev["last_seen"]
        self.devices.append(dev)

    def _local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    def control_device(self, device_id, action, params=None):
        params = params or {}
        dev = next((d for d in self.devices if d["ip"] == device_id), None)
        if not dev:
            return {"status": "error", "message": f"Device {device_id} not found"}

        try:
            if action == "ping":
                flag = "-n" if os.name == "nt" else "-c"
                r = subprocess.run(["ping", flag, "2", dev["ip"]], capture_output=True, text=True, timeout=10)
                return {"status": "ok", "output": r.stdout}

            if action == "http_get":
                import requests
                url = params.get("url", f"http://{dev['ip']}")
                r = requests.get(url, timeout=5)
                return {"status": "ok", "code": r.status_code, "body": r.text[:300]}

            if action == "ssh_exec":
                import paramiko
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(dev["ip"], username=params.get("user", "root"),
                               password=params.get("pass", ""), timeout=10)
                _, stdout, _ = client.exec_command(params.get("cmd", "uptime"))
                output = stdout.read().decode()
                client.close()
                return {"status": "ok", "output": output}

            if action == "wake":
                mac = params.get("mac", "")
                if mac:
                    magic = bytes.fromhex("FF" * 6 + mac.replace(":", "").replace("-", "") * 16)
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    s.sendto(magic, ("255.255.255.255", 9))
                    s.close()
                    return {"status": "ok", "message": "WOL packet sent"}
                return {"status": "error", "message": "MAC required"}

            return {"status": "error", "message": f"Unknown action: {action}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}
