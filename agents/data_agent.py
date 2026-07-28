import os, json, csv, re, sqlite3
from agents.base_agent import BaseAgent
from config import STORAGE_DIR


class DataAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "data_agent",
            "Extract, parse, transform, and analyze data from files, APIs, databases, and web",
        )
        self.capabilities = ["data", "extract", "parse", "convert", "analyze", "db", "api", "scrape", "report"]

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()

        if "extract" in t or "parse" in t:
            fpath = self._extract_filepath(task)
            if fpath and os.path.isfile(fpath):
                return self._parse_file(fpath)
            return "DataAgent: File not found. Usage: extract <filepath>"

        if "convert" in t or "transform" in t:
            fpath = self._extract_filepath(task)
            if fpath and os.path.isfile(fpath):
                return self._convert_file(fpath)
            return "DataAgent: File not found. Usage: convert <filepath>"

        if "fetch" in t or "api" in t or "http" in t:
            urls = re.findall(r'https?://[^\s]+', task)
            if urls:
                return self._fetch_urls(urls)
            return "DataAgent: No URLs found"

        if "db" in t or "sqlite" in t or "sql" in t:
            return self._explore_databases()

        if "analyze" in t:
            fpath = self._extract_filepath(task)
            if fpath and os.path.isfile(fpath):
                return self._analyze_file(fpath)
            return self._analyze_directory(STORAGE_DIR)

        if "scrape" in t:
            urls = re.findall(r'https?://[^\s]+', task)
            if urls:
                return self._scrape(urls[0])
            return "DataAgent: Usage: scrape <url>"

        if "report" in t:
            return self._generate_report()

        return f"DataAgent: Available: extract <file>, convert <file>, fetch <url>, db, analyze [file], scrape <url>, report"

    def _extract_filepath(self, task):
        words = task.split()
        for w in words:
            w = w.strip()
            if os.path.exists(w):
                return w
            for root, dirs, files in os.walk(STORAGE_DIR):
                if w in files:
                    return os.path.join(root, w)
        return None

    def _parse_file(self, fpath):
        ext = os.path.splitext(fpath)[1].lower()
        try:
            if ext == ".json":
                with open(fpath) as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    keys = list(data.keys())[:20]
                    return f"DataAgent: JSON with {len(data)} top-level keys: {keys}"
                elif isinstance(data, list):
                    return f"DataAgent: JSON array with {len(data)} items"
                return f"DataAgent: JSON: {str(data)[:200]}"

            elif ext == ".csv":
                with open(fpath, newline="") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                if rows:
                    return f"DataAgent: CSV {len(rows)} rows, {len(rows[0])} columns: {list(rows[0].keys())}"
                return "DataAgent: Empty CSV"

            elif ext in (".html", ".htm"):
                from html.parser import HTMLParser
                text = []
                class P(HTMLParser):
                    def handle_data(self, d):
                        if d.strip():
                            text.append(d.strip())
                with open(fpath) as f:
                    P().feed(f.read())
                return f"DataAgent: HTML extracted {len(text)} text blocks. First: {text[0][:100] if text else 'N/A'}"

            elif ext == ".xml":
                import xml.etree.ElementTree as ET
                tree = ET.parse(fpath)
                root = tree.getroot()
                return f"DataAgent: XML root: {root.tag}, children: {len(root)}"

            elif ext == ".md":
                with open(fpath) as f:
                    content = f.read()
                headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
                return f"DataAgent: Markdown with {len(headers)} headers: {headers[:10]}"

            elif ext == ".log":
                with open(fpath) as f:
                    lines = f.readlines()
                errors = [l for l in lines if "error" in l.lower()]
                return f"DataAgent: Log file {len(lines)} lines, {len(errors)} errors"

            else:
                with open(fpath, errors="replace") as f:
                    content = f.read(2000)
                return f"DataAgent: Raw text ({len(content)} chars): {content[:200]}"

        except Exception as e:
            return f"DataAgent: Parse error: {e}"

    def _convert_file(self, fpath):
        ext = os.path.splitext(fpath)[1].lower()
        base = os.path.splitext(fpath)[0]
        try:
            if ext == ".csv":
                with open(fpath) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                out_path = base + ".json"
                with open(out_path, "w") as f:
                    json.dump(rows, f, indent=2)
                return f"DataAgent: Converted CSV -> JSON ({len(rows)} rows)"

            elif ext == ".json":
                with open(fpath) as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    out_path = base + ".csv"
                    with open(out_path, "w", newline="") as f:
                        w = csv.DictWriter(f, fieldnames=data[0].keys())
                        w.writeheader()
                        w.writerows(data)
                    return f"DataAgent: Converted JSON -> CSV ({len(data)} rows)"
                return "DataAgent: JSON must be an array of objects to convert to CSV"

            return f"DataAgent: Conversion not supported for {ext}"

        except Exception as e:
            return f"DataAgent: Conversion error: {e}"

    def _fetch_urls(self, urls):
        try:
            import requests
            results = []
            for url in urls[:5]:
                try:
                    r = requests.get(url, timeout=15)
                    ct = r.headers.get("Content-Type", "unknown")
                    results.append(f"{url}: {r.status_code}, {len(r.content)} bytes, type: {ct}")
                except Exception as e:
                    results.append(f"{url}: Error - {e}")
            return "DataAgent: Fetch results:\n" + "\n".join(results)
        except ImportError:
            return "DataAgent: requests not installed"

    def _explore_databases(self):
        dbs = []
        for root, dirs, files in os.walk(STORAGE_DIR):
            for f in files:
                if f.endswith((".db", ".sqlite")):
                    dbs.append(os.path.join(root, f))
        if not dbs:
            return "DataAgent: No SQLite databases found"
        results = []
        for db_path in dbs[:5]:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()
                results.append(f"{os.path.basename(db_path)}: {len(tables)} tables")
                for t in tables[:5]:
                    results.append(f"  - {t[0]}")
            except Exception:
                pass
        return "DataAgent: Databases:\n" + "\n".join(results)

    def _analyze_file(self, fpath):
        stat = os.stat(fpath)
        ext = os.path.splitext(fpath)[1]
        info = f"Name: {os.path.basename(fpath)}\nSize: {stat.st_size:,} bytes\nType: {ext or 'N/A'}\nModified: {stat.st_mtime}"
        return "DataAgent: File Analysis:\n" + info

    def _analyze_directory(self, path):
        total = sum(len(files) for _, _, files in os.walk(path))
        size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(path) for f in fs if os.path.isfile(os.path.join(r, f)))
        return f"DataAgent: Directory: {total} files, {size / 1024 / 1024:.1f} MB"

    def _scrape(self, url):
        try:
            import requests
            from html.parser import HTMLParser
            class LinkParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.links = []
                    self.text = []
                    self._capture = False
                def handle_starttag(self, tag, attrs):
                    if tag == "a":
                        for k, v in attrs:
                            if k == "href":
                                self.links.append(v)
                    if tag in ("p", "h1", "h2", "h3", "h4", "title", "li"):
                        self._capture = True
                def handle_endtag(self, tag):
                    if tag in ("p", "h1", "h2", "h3", "h4", "title", "li"):
                        self._capture = False
                def handle_data(self, data):
                    if self._capture and data.strip():
                        self.text.append(data.strip())
            r = requests.get(url, timeout=15)
            parser = LinkParser()
            parser.feed(r.text)
            return f"DataAgent: Scraped {url}\nTitle: {parser.text[0] if parser.text else 'N/A'}\nLinks: {len(parser.links)}\nContent: {' '.join(parser.text[:10])[:300]}"
        except Exception as e:
            return f"DataAgent: Scrape failed: {e}"

    def _generate_report(self):
        files = []
        for root, dirs, fs in os.walk(STORAGE_DIR):
            for f in fs:
                fpath = os.path.join(root, f)
                try:
                    files.append((fpath, os.path.getsize(fpath)))
                except Exception:
                    pass
        total_files = len(files)
        total_size = sum(s for _, s in files)
        largest = sorted(files, key=lambda x: -x[1])[:5]
        ext_counts = {}
        for fpath, _ in files:
            ext = os.path.splitext(fpath)[1] or "no_ext"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        report = [
            f"DataAgent: Storage Report",
            f"Total files: {total_files}",
            f"Total size: {total_size / 1024 / 1024:.1f} MB",
            f"File types: {dict(sorted(ext_counts.items(), key=lambda x: -x[1])[:10])}",
            f"Largest files:",
        ]
        for fpath, sz in largest:
            report.append(f"  {os.path.relpath(fpath, STORAGE_DIR)} ({sz / 1024:.1f} KB)")
        return "\n".join(report)
