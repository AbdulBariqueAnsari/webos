import os, json, subprocess, threading, time
from datetime import datetime


class DockerManager:
    def __init__(self):
        self._available = self._check_docker()

    def _check_docker(self):
        try:
            r = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    @property
    def available(self):
        return self._available

    def _run(self, cmd):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {"status": "ok" if r.returncode == 0 else "error", "stdout": r.stdout, "stderr": r.stderr}
        except subprocess.TimeoutExpired:
            return {"status": "error", "stdout": "", "stderr": "Command timed out"}
        except FileNotFoundError:
            return {"status": "error", "stdout": "", "stderr": "Docker not found"}
        except Exception as e:
            return {"status": "error", "stdout": "", "stderr": str(e)}

    def list_containers(self, all=False):
        cmd = ["docker", "ps", "--format", "{{json .}}"]
        if all:
            cmd.append("-a")
        r = self._run(cmd)
        if r["status"] == "ok":
            containers = []
            for line in r["stdout"].strip().split("\n"):
                if line.strip():
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            return {"containers": containers}
        return {"error": r["stderr"]}

    def container_action(self, container_id, action):
        actions = {"start": "start", "stop": "stop", "restart": "restart", "pause": "pause", "unpause": "unpause", "kill": "kill", "rm": "rm -f"}
        cmd = ["docker"]
        if action in actions:
            cmd.extend(actions[action].split())
            cmd.append(container_id)
            return self._run(cmd)
        return {"status": "error", "stdout": "", "stderr": f"Unknown action: {action}"}

    def container_logs(self, container_id, tail=50):
        return self._run(["docker", "logs", "--tail", str(tail), container_id])

    def container_stats(self, container_id):
        r = self._run(["docker", "stats", "--no-stream", "--format", "{{json .}}", container_id])
        if r["status"] == "ok" and r["stdout"].strip():
            try:
                return {"status": "ok", "stats": json.loads(r["stdout"].strip())}
            except json.JSONDecodeError:
                pass
        return {"error": r["stderr"]}

    def list_images(self):
        r = self._run(["docker", "images", "--format", "{{json .}}"])
        if r["status"] == "ok":
            images = []
            for line in r["stdout"].strip().split("\n"):
                if line.strip():
                    try:
                        images.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            return {"images": images}
        return {"error": r["stderr"]}

    def pull_image(self, image):
        return self._run(["docker", "pull", image])

    def system_info(self):
        r = self._run(["docker", "info", "--format", "{{json .}}"])
        if r["status"] == "ok" and r["stdout"].strip():
            try:
                return {"status": "ok", "info": json.loads(r["stdout"].strip())}
            except json.JSONDecodeError:
                pass
        # Fallback: parse text output
        r2 = self._run(["docker", "info"])
        if r2["status"] == "ok":
            lines = r2["stdout"].split("\n")
            info = {}
            for line in lines:
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip()] = v.strip()
            return {"status": "ok", "info": info}
        return {"error": r2["stderr"]}

    def compose_list(self):
        r = self._run(["docker", "compose", "ls", "--format", "json"])
        if r["status"] == "ok":
            try:
                return {"projects": json.loads(r["stdout"]) if r["stdout"].strip() else []}
            except json.JSONDecodeError:
                return {"projects": []}
        return {"error": r["stderr"]}
