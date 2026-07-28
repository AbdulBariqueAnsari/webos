import os, json, uuid, time, threading
from datetime import datetime, timedelta

SHARES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "storage", "shares.json")
SHARES_LOCK = threading.Lock()


class FileShare:
    def __init__(self):
        self.shares = self._load()

    def _load(self):
        if os.path.exists(SHARES_FILE):
            try:
                with open(SHARES_FILE) as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        os.makedirs(os.path.dirname(SHARES_FILE), exist_ok=True)
        with open(SHARES_FILE, "w") as f:
            json.dump(self.shares, f, indent=2)

    def create(self, filepath, expiry_hours=24, password=""):
        if not os.path.isfile(filepath):
            return {"status": "error", "message": "File not found"}
        share_id = uuid.uuid4().hex[:12]
        expires = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
        share = {
            "id": share_id,
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "size": os.path.getsize(filepath),
            "created": datetime.now().isoformat(),
            "expires": expires,
            "password": password,
            "downloads": 0,
        }
        with SHARES_LOCK:
            self.shares.append(share)
            self._cleanup()
            self._save()
        return {
            "status": "ok",
            "share_id": share_id,
            "url": f"/api/shares/{share_id}",
            "expires": expires,
        }

    def get(self, share_id):
        with SHARES_LOCK:
            for s in self.shares:
                if s["id"] == share_id:
                    if datetime.fromisoformat(s["expires"]) < datetime.now():
                        self.shares.remove(s)
                        self._save()
                        return {"status": "error", "message": "Share expired"}
                    return {"status": "ok", "share": s}
            return {"status": "error", "message": "Share not found"}

    def download(self, share_id):
        s = self.get(share_id)
        if s["status"] != "ok":
            return s
        share = s["share"]
        share["downloads"] += 1
        with SHARES_LOCK:
            self._save()
        return {"status": "ok", "filepath": share["filepath"], "filename": share["filename"], "size": share["size"]}

    def list(self):
        with SHARES_LOCK:
            self._cleanup()
            return [{
                "id": s["id"],
                "filename": s["filename"],
                "size": s["size"],
                "created": s["created"],
                "expires": s["expires"],
                "downloads": s["downloads"],
            } for s in self.shares]

    def delete(self, share_id):
        with SHARES_LOCK:
            self.shares = [s for s in self.shares if s["id"] != share_id]
            self._save()
        return {"status": "ok"}

    def _cleanup(self):
        now = datetime.now()
        self.shares = [s for s in self.shares if datetime.fromisoformat(s["expires"]) > now]


file_share = FileShare()
