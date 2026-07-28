import os, json, subprocess, psutil, platform, shutil
from agents.base_agent import BaseAgent


class SystemAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "system_agent",
            "Monitor and manage system resources, processes, services, packages, and updates",
        )
        self.capabilities = ["system", "monitor", "process", "service", "package", "update", "resource", "info"]

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()

        if "info" in t or "overview" in t:
            return self._system_info()

        if "cpu" in t:
            return self._cpu_info()

        if "memory" in t or "ram" in t:
            return self._memory_info()

        if "disk" in t:
            return self._disk_info()

        if "process" in t or "top" in t:
            count = 20
            return self._process_list(count)

        if "service" in t:
            return self._service_list()

        if "package" in t or "install" in t:
            pkg = task.replace("install", "").replace("package", "").strip()
            if pkg:
                return self._install_package(pkg)
            return "SystemAgent: Usage: install <package-name>"

        if "update" in t or "upgrade" in t:
            return self._check_updates()

        if "monitor" in t or "health" in t:
            return self._system_health()

        return f"SystemAgent: Available: info, cpu, memory, disk, process, service, install <pkg>, update, monitor"

    def _system_info(self):
        boot = psutil.boot_time()
        from datetime import datetime
        info = {
            "Hostname": socket.gethostname() if hasattr(__import__("socket"), "gethostname") else "N/A",
            "Platform": platform.platform(),
            "Python": platform.python_version(),
            "CPU Cores": psutil.cpu_count(),
            "CPU Usage": f"{psutil.cpu_percent()}%",
            "Memory": f"{psutil.virtual_memory().percent}% used",
            "Disk": f"{psutil.disk_usage('/').percent}% used",
            "Boot Time": datetime.fromtimestamp(boot).strftime("%Y-%m-%d %H:%M:%S"),
            "Uptime": self._format_uptime(boot),
        }
        return "SystemAgent: System Info\n" + "\n".join(f"  {k}: {v}" for k, v in info.items())

    import socket

    def _cpu_info(self):
        return f"SystemAgent: CPU\n  Cores: {psutil.cpu_count()} (logical: {psutil.cpu_count(logical=True)})\n  Usage: {psutil.cpu_percent(interval=0.5)}%\n  Frequency: {psutil.cpu_freq().current:.0f} MHz" if hasattr(psutil, "cpu_freq") else "N/A"

    def _memory_info(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return f"SystemAgent: Memory\n  RAM: {mem.used / 1024**3:.1f}/{mem.total / 1024**3:.1f} GB ({mem.percent}%)\n  Swap: {swap.used / 1024**3:.1f}/{swap.total / 1024**3:.1f} GB ({swap.percent}%)\n  Available: {mem.available / 1024**3:.1f} GB"

    def _disk_info(self):
        disks = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append(f"  {part.device} mounted at {part.mountpoint}: {usage.used / 1024**3:.1f}/{usage.total / 1024**3:.1f} GB ({usage.percent}%)")
            except Exception:
                disks.append(f"  {part.device} mounted at {part.mountpoint}")
        return "SystemAgent: Disk\n" + "\n".join(disks)

    def _process_list(self, limit=20):
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                procs.append(p.info)
            except Exception:
                pass
        procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
        lines = [f"  {'PID':<6} {'CPU%':<6} {'MEM%':<6} {'STATUS':<10} NAME"]
        for p in procs[:limit]:
            lines.append(f"  {p['pid']:<6} {p.get('cpu_percent', 0):<6.1f} {p.get('memory_percent', 0):<6.1f} {p.get('status', '?'):<10} {p['name'][:30]}")
        return "SystemAgent: Top Processes\n" + "\n".join(lines)

    def _service_list(self):
        services = {}
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                for conn in proc.connections():
                    if conn.status == "LISTEN":
                        services[f"{proc.info['name']}:{conn.laddr.port}"] = proc.info["pid"]
            except Exception:
                pass
        if not services:
            return "SystemAgent: No listening services found"
        lines = [f"  {'SERVICE':<25} {'PID':<8}", "  " + "-" * 33]
        for name, pid in sorted(services.items()):
            lines.append(f"  {name:<25} {pid:<8}")
        return "SystemAgent: Listening Services\n" + "\n".join(lines)

    def _install_package(self, pkg):
        try:
            result = subprocess.run(["pip", "install", pkg], capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return f"SystemAgent: Installed {pkg} successfully"
            return f"SystemAgent: Install failed: {result.stderr[:200]}"
        except Exception as e:
            return f"SystemAgent: Install error: {e}"

    def _check_updates(self):
        try:
            result = subprocess.run(["pip", "list", "--outdated"], capture_output=True, text=True, timeout=30)
            lines = [l for l in result.stdout.split("\n") if l.strip()][2:]
            if lines:
                return f"SystemAgent: {len(lines)} packages can be updated:\n" + "\n".join(lines[:10])
            return "SystemAgent: All packages up to date"
        except Exception as e:
            return f"SystemAgent: Update check failed: {e}"

    def _system_health(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        status = "Healthy" if cpu < 80 and mem < 80 and disk < 90 else "Warning"
        return f"SystemAgent: System Health [{status}]\n  CPU: {cpu}%\n  Memory: {mem}%\n  Disk: {disk}%\n  Status: {'✅' if status == 'Healthy' else '⚠️'}{status}"

    def _format_uptime(self, boot):
        import time
        seconds = time.time() - boot
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{days}d {hours}h {mins}m"
