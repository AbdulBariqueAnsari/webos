import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STORAGE_DIR


class WebDAVServer:
    def __init__(self, host="0.0.0.0", port=8081):
        self.host = host
        self.port = port
        self.server = None

    def start(self):
        try:
            from wsgidav.wsgidav_app import WsgiDAVApp
            from wsgidav.fs_dav_provider import FilesystemProvider

            provider = FilesystemProvider(STORAGE_DIR, readonly=False)
            config = {
                "host": self.host,
                "port": self.port,
                "provider_mapping": {"/": provider},
                "verbose": 0,
            }
            app = WsgiDAVApp(config)
            from cheroot import wsgi
            self.server = wsgi.Server((self.host, self.port), app)
            print(f"[WebDAV] Server started on http://{self.host}:{self.port}")
            self.server.start()
        except Exception as e:
            print(f"[WebDAV] WsgiDAV failed ({e}). Starting simple WebDAV server...")
            self._simple_webdav()

    def _simple_webdav(self):
        from http.server import HTTPServer, SimpleHTTPRequestHandler
        import threading

        class WebDAVHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=STORAGE_DIR, **kwargs)

            def do_PROPFIND(self):
                self.send_response(207)
                self.send_header("Content-Type", "application/xml; charset=utf-8")
                self.send_header("DAV", "1,2")
                self.end_headers()
                path = self.translate_path(self.path)
                if os.path.isdir(path):
                    import xml.etree.ElementTree as ET
                    root = ET.Element("multistatus", xmlns="DAV:")
                    for entry in os.scandir(path):
                        resp = ET.SubElement(root, "response")
                        href = ET.SubElement(resp, "href")
                        href.text = os.path.join(self.path, entry.name)
                        propstat = ET.SubElement(resp, "propstat")
                        prop = ET.SubElement(propstat, "prop")
                        ET.SubElement(prop, "displayname").text = entry.name
                        res_type = ET.SubElement(prop, "resourcetype")
                        if entry.is_dir():
                            ET.SubElement(res_type, "collection")
                        ET.SubElement(prop, "getcontentlength").text = str(entry.stat().st_size)
                        ET.SubElement(propstat, "status").text = "HTTP/1.1 200 OK"
                    self.wfile.write(ET.tostring(root, encoding="utf-8"))

            def do_MKCOL(self):
                path = self.translate_path(self.path)
                try:
                    os.makedirs(path, exist_ok=True)
                    self.send_response(201)
                    self.end_headers()
                except Exception:
                    self.send_response(405)
                    self.end_headers()

            def do_PUT(self):
                length = int(self.headers.get("Content-Length", 0))
                path = self.translate_path(self.path)
                with open(path, "wb") as f:
                    f.write(self.rfile.read(length))
                self.send_response(201)
                self.end_headers()

            def do_DELETE(self):
                path = self.translate_path(self.path)
                try:
                    if os.path.isdir(path):
                        import shutil
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    self.send_response(204)
                    self.end_headers()
                except Exception:
                    self.send_response(404)
                    self.end_headers()

            def do_MOVE(self):
                dest_header = self.headers.get("Destination", "")
                from urllib.parse import urlparse
                dest_path = urlparse(dest_header).path
                dest = self.translate_path(dest_path)
                src = self.translate_path(self.path)
                try:
                    os.rename(src, dest)
                    self.send_response(204)
                    self.end_headers()
                except Exception:
                    self.send_response(502)
                    self.end_headers()

        server = HTTPServer((self.host, self.port), WebDAVHandler)
        print(f"[WebDAV] Simple server on http://{self.host}:{self.port}")
        server.serve_forever()

    def stop(self):
        if self.server:
            self.server.stop()
