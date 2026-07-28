import os, sys, json, subprocess, shutil, time, uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STORAGE_DIR

RECYCLE_DIR = os.path.join(STORAGE_DIR, ".trash")
BOOKMARKS_FILE = os.path.join(STORAGE_DIR, ".bookmarks.json")
RECENT_FILE = os.path.join(STORAGE_DIR, ".recent.json")


def resolve_path(path=""):
    if not path or path == "/storage":
        return STORAGE_DIR
    if path.startswith("/storage/"):
        path = path[9:]
    full = os.path.join(STORAGE_DIR, path.lstrip("/\\"))
    full = os.path.normpath(full)
    if not full.startswith(os.path.normpath(STORAGE_DIR)):
        return STORAGE_DIR
    return full


def list_dir(path=""):
    full = resolve_path(path)
    if not os.path.exists(full):
        return {"error": "Path not found", "items": []}
    items = []
    try:
        for entry in os.scandir(full):
            if entry.name.startswith("."):
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": entry.path,
                "rel_path": os.path.relpath(entry.path, STORAGE_DIR),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if not entry.is_dir() else 0,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
            })
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    except Exception as e:
        return {"error": str(e), "items": []}
    return {
        "items": items,
        "path": full,
        "rel_path": os.path.relpath(full, STORAGE_DIR),
        "parent": os.path.dirname(full) if full != STORAGE_DIR else None,
        "parent_rel": os.path.relpath(os.path.dirname(full), STORAGE_DIR) if full != STORAGE_DIR else None,
        "storage": STORAGE_DIR,
    }


def read_file(path=""):
    full = resolve_path(path)
    if not os.path.isfile(full):
        return {"error": "File not found"}
    try:
        with open(full, "rb") as f:
            content = f.read()
        text = content.decode("utf-8", errors="replace")
        return {"content": text, "size": len(content), "path": full, "name": os.path.basename(full)}
    except Exception as e:
        return {"error": str(e)}


def write_file(path="", content=""):
    full = resolve_path(path)
    try:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        add_recent(full)
        return {"status": "ok", "path": full}
    except Exception as e:
        return {"error": str(e)}


def delete_file(path=""):
    full = resolve_path(path)
    if not os.path.exists(full):
        return {"error": "Not found"}
    # Move to recycle bin instead of permanent delete
    os.makedirs(RECYCLE_DIR, exist_ok=True)
    trash_name = f"{os.path.basename(full)}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    trash_path = os.path.join(RECYCLE_DIR, trash_name)
    try:
        shutil.move(full, trash_path)
        return {"status": "ok", "trash": trash_name}
    except Exception as e:
        return {"error": str(e)}


def permanent_delete(path=""):
    full = resolve_path(path)
    try:
        if os.path.isdir(full):
            shutil.rmtree(full)
        else:
            os.remove(full)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}


def move_file(src="", dst=""):
    full_src = resolve_path(src)
    full_dst = resolve_path(dst)
    try:
        os.makedirs(os.path.dirname(full_dst), exist_ok=True)
        shutil.move(full_src, full_dst)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}


def copy_file(src="", dst=""):
    full_src = resolve_path(src)
    full_dst = resolve_path(dst)
    try:
        os.makedirs(os.path.dirname(full_dst), exist_ok=True)
        if os.path.isdir(full_src):
            shutil.copytree(full_src, full_dst)
        else:
            shutil.copy2(full_src, full_dst)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}


def search_files(query="", base=""):
    full = resolve_path(base)
    results = []
    query = query.lower()
    try:
        for root, dirs, files in os.walk(full):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if query in f.lower() or query in root.lower():
                    fpath = os.path.join(root, f)
                    try:
                        results.append({
                            "name": f, "path": fpath,
                            "rel_path": os.path.relpath(fpath, STORAGE_DIR),
                            "size": os.path.getsize(fpath),
                            "modified": os.path.getmtime(fpath),
                        })
                    except Exception:
                        pass
                    if len(results) >= 100:
                        break
            if len(results) >= 100:
                break
    except Exception:
        pass
    return {"results": results, "query": query, "count": len(results)}


def file_info(path=""):
    full = resolve_path(path)
    if not os.path.exists(full):
        return {"error": "Not found"}
    stat = os.stat(full)
    import mimetypes
    mime = mimetypes.guess_type(full)[0] or "application/octet-stream"
    return {
        "name": os.path.basename(full), "path": full,
        "rel_path": os.path.relpath(full, STORAGE_DIR),
        "is_dir": os.path.isdir(full), "size": stat.st_size,
        "modified": stat.st_mtime, "created": stat.st_ctime,
        "mime": mime,
    }


def add_recent(path):
    try:
        recent = []
        if os.path.exists(RECENT_FILE):
            with open(RECENT_FILE) as f:
                recent = json.load(f)
        recent.insert(0, {"path": path, "time": datetime.now().isoformat(), "name": os.path.basename(path)})
        recent = recent[:50]
        os.makedirs(os.path.dirname(RECENT_FILE), exist_ok=True)
        with open(RECENT_FILE, "w") as f:
            json.dump(recent, f, indent=2)
    except Exception:
        pass


def get_recent(limit=20):
    if not os.path.exists(RECENT_FILE):
        return []
    try:
        with open(RECENT_FILE) as f:
            return json.load(f)[:limit]
    except Exception:
        return []


def trash_list():
    if not os.path.exists(RECYCLE_DIR):
        return []
    items = []
    for entry in os.scandir(RECYCLE_DIR):
        if entry.is_file() or entry.is_dir():
            stat = entry.stat()
            orig = entry.name.rsplit("_", 2)[0] if "_" in entry.name else entry.name
            items.append({
                "trash_name": entry.name,
                "original_name": orig,
                "size": stat.st_size if not entry.is_dir() else 0,
                "deleted": stat.st_mtime,
                "is_dir": entry.is_dir(),
            })
    return sorted(items, key=lambda x: x["deleted"], reverse=True)


def trash_restore(trash_name=""):
    src = os.path.join(RECYCLE_DIR, trash_name)
    if not os.path.exists(src):
        return {"error": "Not found"}
    orig = trash_name.rsplit("_", 2)[0]
    dst = os.path.join(STORAGE_DIR, orig)
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        return {"status": "ok", "restored": orig}
    except Exception as e:
        return {"error": str(e)}


def trash_empty():
    if os.path.exists(RECYCLE_DIR):
        shutil.rmtree(RECYCLE_DIR)
        os.makedirs(RECYCLE_DIR, exist_ok=True)
    return {"status": "ok"}


def bookmarks_list():
    if not os.path.exists(BOOKMARKS_FILE):
        return []
    try:
        with open(BOOKMARKS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def bookmark_add(path="", name=""):
    bookmarks = bookmarks_list()
    full = resolve_path(path)
    if not name:
        name = os.path.basename(full)
    bookmarks.append({"path": full, "name": name, "time": datetime.now().isoformat()})
    with open(BOOKMARKS_FILE, "w") as f:
        json.dump(bookmarks, f, indent=2)
    return {"status": "ok"}


def bookmark_remove(path=""):
    full = resolve_path(path)
    bookmarks = [b for b in bookmarks_list() if b["path"] != full]
    with open(BOOKMARKS_FILE, "w") as f:
        json.dump(bookmarks, f, indent=2)
    return {"status": "ok"}
