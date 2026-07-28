import os, json, socket, subprocess, threading
from agents.base_agent import BaseAgent
from devices.device_manager import DeviceManager


class DeviceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "device_agent",
            "Discover, monitor, and control network devices via SSH, SNMP, WOL, and HTTP",
        )
        self.capabilities = ["device", "iot", "ssh", "wol", "discover", "monitor", "smart"]

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()
        dm = DeviceManager()

        if "list" in t or "known" in t:
            devices = dm.list_devices()
            return f"DeviceAgent: {len(devices)} known devices\n" + json.dumps(devices, indent=2)[:1000]

        if "scan" in t or "discover" in t:
            devices = dm.scan_network()
            return f"DeviceAgent: Found {len(devices)} devices on network"

        if "ssh" in t:
            parts = task.split()
            host = None
            cmd = "uptime"
            for i, p in enumerate(parts):
                if p == "ssh" and i + 1 < len(parts):
                    host = parts[i + 1]
                if p == "cmd" and i + 1 < len(parts):
                    cmd = " ".join(parts[i + 1:])
            if not host:
                return "DeviceAgent: Usage: ssh <host> cmd <command>"
            return self._ssh_exec(host, cmd)

        if "wol" in t or "wake" in t:
            for word in task.split():
                if ":" in word and len(word) == 17:
                    return dm.control_device("", "wake", {"mac": word}).get("message", "WOL sent")
            return "DeviceAgent: Usage: wol <mac-address>"

        if "ping" in t:
            for word in task.split():
                if "." in word and word.count(".") == 3:
                    return dm.control_device(word, "ping").get("output", "Ping failed")
            return "DeviceAgent: Usage: ping <ip-address>"

        return f"DeviceAgent: Available: list, scan, ssh <host> cmd <cmd>, wol <mac>, ping <ip>"

    def _ssh_exec(self, host, cmd):
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, username="root", password="", timeout=10, look_for_keys=True)
            _, stdout, stderr = client.exec_command(cmd)
            output = stdout.read().decode().strip() or stderr.read().decode().strip()
            client.close()
            return f"DeviceAgent: SSH {host}\n$ {cmd}\n{output[:1000]}"
        except ImportError:
            return "DeviceAgent: paramiko not installed"
        except Exception as e:
            return f"DeviceAgent: SSH failed: {e}"
