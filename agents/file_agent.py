import os, json, hashlib, mimetypes, shutil
from datetime import datetime
from agents.base_agent import BaseAgent
from config import STORAGE_DIR


class FileAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "file_agent",
            "Advanced file management: organize, search, analyze, convert, compress, deduplicate",
        )
        self.capabilities = ["file", "organize", "search", "clean", "duplicate", "backup", "compress", "convert", "sync"]

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()

        if "organize" in t or "sort" in t:
            path = self._extract_path(task) or STORAGE_DIR
            return self._organize(path)

        if "search" in t or "find" in t:
            query = task.replace("search", "").replace("find", "").strip()
            path = self._extract_path(task) or STORAGE_DIR
            return self._deep_search(path, query)

        if "clean" in t or "temp" in t:
            path = self._extract_path(task) or STORAGE_DIR
            return self._clean(path)

        if "duplicate" in t or "dedup" in t:
            path = self._extract_path(task) or STORAGE_DIR
            return self._find_duplicates(path)

        if "backup" in t:
            src = STORAGE_DIR
            dst = os.path.join(STORAGE_DIR, "_backup", datetime.now().strftime("%Y%m%d_%H%M%S"))
            return self._backup(src, dst)

        if "compress" in t or "zip" in t:
            path = self._extract_path(task) or STORAGE_DIR
            return self._compress(path)

        if "analyze" in t or "stats" in t:
            path = self._extract_path(task) or STORAGE_DIR
            return self._analyze(path)

        if "sync" in t:
            return "FileAgent: Sync requires source and destination paths"

        return f"FileAgent: Unknown task. Available: organize, search <q>, clean, duplicate, backup, compress, analyze, sync"

    def _extract_path(self, task):
        for word in task.split():
            if "/" in word or "\\" in word:
                return word.strip()
        return None

    def _organize(self, base_path):
        ext_map = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff"],
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"],
            "Archives": [".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz"],
            "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
            "Video": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
            "Code": [".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".java", ".go", ".rs", ".sh", ".bat", ".sql"],
            "Data": [".json", ".xml", ".csv", ".yaml", ".yml", ".db", ".sqlite"],
            "Config": [".ini", ".cfg", ".conf", ".toml", ".env"],
        }
        moved = 0
        for entry in os.scandir(base_path):
            if entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                target = "Other"
                for cat, exts in ext_map.items():
                    if ext in exts:
                        target = cat
                        break
                dest_dir = os.path.join(base_path, target)
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, entry.name)
                if not os.path.exists(dest):
                    shutil.move(entry.path, dest)
                    moved += 1
        return f"FileAgent: Organized {moved} files into categories: {list(ext_map.keys())} + Other"

    def _deep_search(self, base_path, query):
        results = []
        for root, dirs, files in os.walk(base_path):
            for f in files:
                if query.lower() in f.lower():
                    fpath = os.path.join(root, f)
                    try:
                        results.append({"name": f, "path": fpath, "size": os.path.getsize(fpath)})
                    except Exception:
                        pass
                    if len(results) >= 50:
                        break
            if len(results) >= 50:
                break
        return f"FileAgent: Found {len(results)} files matching '{query}'"

    def _clean(self, base_path):
        removed = 0
        patterns = ["tmp", "temp", "~", ".bak", ".swp", ".log", "__pycache__"]
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in ("_backup",)]
            for f in files:
                if any(p in f.lower() for p in patterns):
                    try:
                        os.remove(os.path.join(root, f))
                        removed += 1
                    except Exception:
                        pass
        return f"FileAgent: Removed {removed} temporary/unnecessary files"

    def _find_duplicates(self, base_path):
        hashes = {}
        duplicates = []
        total = 0
        for root, dirs, files in os.walk(base_path):
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    h = hashlib.md5()
                    with open(fpath, "rb") as fh:
                        h.update(fh.read(8192))
                    digest = h.hexdigest()
                    if digest in hashes:
                        duplicates.append({"original": hashes[digest], "duplicate": fpath, "size": os.path.getsize(fpath)})
                        total += os.path.getsize(fpath)
                    else:
                        hashes[digest] = fpath
                except Exception:
                    pass
        return f"FileAgent: Found {len(duplicates)} duplicate pairs ({total / 1024 / 1024:.1f} MB wasted)"

    def _backup(self, src, dst):
        try:
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("_backup"))
            return f"FileAgent: Backup created at {dst}"
        except Exception as e:
            return f"FileAgent: Backup failed: {e}"

    def _compress(self, path):
        if os.path.isfile(path):
            import zipfile
            zip_path = path + ".zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(path, os.path.basename(path))
            return f"FileAgent: Compressed to {zip_path}"
        return "FileAgent: Compress works on individual files"

    def _analyze(self, path):
        total_files = 0
        total_size = 0
        ext_counts = {}
        for root, dirs, files in os.walk(path):
            total_files += len(files)
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    sz = os.path.getsize(fpath)
                    total_size += sz
                    ext = os.path.splitext(f)[1].lower() or "no_ext"
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
                except Exception:
                    pass
        top_exts = sorted(ext_counts.items(), key=lambda x: -x[1])[:10]
        return f"FileAgent: {total_files} files, {total_size / 1024 / 1024:.1f} MB. Top types: {dict(top_exts)}"
