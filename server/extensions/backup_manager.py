import os, json, threading, time
from datetime import datetime, timedelta
from server.database import db
from server.ws_server import WebSocketServer


class BackupManager:
    def __init__(self):
        self._running = False
        self._worker = None

    def create_backup(self, name="", paths=None):
        import shutil
        from config import STORAGE_DIR

        if paths is None:
            paths = [STORAGE_DIR]

        backup_dir = os.path.join(STORAGE_DIR, "_backups")
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = name or f"backup_{ts}"
        dest = os.path.join(backup_dir, backup_name)
        os.makedirs(dest, exist_ok=True)

        total_files = 0
        total_size = 0
        for src in paths:
            if os.path.isfile(src):
                shutil.copy2(src, dest)
                total_files += 1
                total_size += os.path.getsize(src)
            elif os.path.isdir(src):
                for root, dirs, files in os.walk(src):
                    for f in files:
                        fpath = os.path.join(root, f)
                        rel = os.path.relpath(fpath, src)
                        dest_file = os.path.join(dest, os.path.basename(src), rel)
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        try:
                            shutil.copy2(fpath, dest_file)
                            total_files += 1
                            total_size += os.path.getsize(fpath)
                        except Exception:
                            pass

        info = {
            "name": backup_name,
            "created": ts,
            "path": dest,
            "files": total_files,
            "size": total_size,
        }
        info_path = os.path.join(dest, "_backup_info.json")
        with open(info_path, "w") as f:
            json.dump(info, f, indent=2)

        db.add_notification("Backup Created", f"{backup_name} ({total_files} files, {total_size/1024/1024:.1f} MB)", "success")
        return {"status": "ok", "backup": info}

    def list_backups(self):
        backup_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "storage", "_backups",
        )
        backups = []
        if os.path.isdir(backup_dir):
            for entry in os.scandir(backup_dir):
                if entry.is_dir():
                    info_path = os.path.join(entry.path, "_backup_info.json")
                    if os.path.exists(info_path):
                        try:
                            with open(info_path) as f:
                                info = json.load(f)
                            backups.append(info)
                        except Exception:
                            backups.append({"name": entry.name, "created": "unknown", "path": entry.path})
                    else:
                        backups.append({"name": entry.name, "created": "unknown", "path": entry.path})
        return sorted(backups, key=lambda x: x.get("created", ""), reverse=True)

    def restore_backup(self, name):
        backup_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "storage", "_backups", name,
        )
        if not os.path.isdir(backup_dir):
            return {"status": "error", "message": "Backup not found"}

        import shutil
        from config import STORAGE_DIR

        for entry in os.scandir(backup_dir):
            if entry.name != "_backup_info.json":
                dest = os.path.join(STORAGE_DIR, entry.name)
                try:
                    if os.path.exists(dest):
                        if os.path.isdir(dest):
                            shutil.rmtree(dest)
                        else:
                            os.remove(dest)
                    if entry.is_dir():
                        shutil.copytree(entry.path, dest)
                    else:
                        shutil.copy2(entry.path, dest)
                except Exception as e:
                    return {"status": "error", "message": str(e)}

        db.add_notification("Backup Restored", name, "success")
        return {"status": "ok", "message": f"Restored {name}"}

    def delete_backup(self, name):
        import shutil
        backup_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "storage", "_backups", name,
        )
        if os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir)
            return {"status": "ok"}
        return {"status": "error", "message": "Not found"}

    def schedule(self, interval_hours=24, paths=None):
        if self._running:
            return {"status": "error", "message": "Scheduler already running"}

        self._running = True

        def _run():
            while self._running:
                self.create_backup(name=f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}", paths=paths)
                for i in range(interval_hours * 3600):
                    if not self._running:
                        break
                    time.sleep(1)

        self._worker = threading.Thread(target=_run, daemon=True)
        self._worker.start()
        return {"status": "ok", "message": f"Backup scheduled every {interval_hours}h"}

    def stop_schedule(self):
        self._running = False
        return {"status": "ok"}


backup_manager = BackupManager()
