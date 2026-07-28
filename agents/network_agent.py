import os, json, socket, subprocess, threading, time
from agents.base_agent import BaseAgent


class NetworkAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "network_agent",
            "Advanced network diagnostics, speed tests, DNS, HTTP checking, port scanning, tracing",
        )
        self.capabilities = ["network", "ping", "scan", "dns", "trace", "http", "speed", "whois", "ssl"]

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()

        if "ping" in t:
            host = self._extract_host(task) or "8.8.8.8"
            return self._ping(host)

        if "port" in t or "scan" in t:
            host = self._extract_host(task) or "127.0.0.1"
            return self._port_scan(host)

        if "dns" in t or "resolve" in t:
            host = self._extract_host(task) or "google.com"
            return self._dns_lookup(host)

        if "trace" in t or "traceroute" in t or "tracert" in t:
            host = self._extract_host(task) or "google.com"
            return self._trace(host)

        if "http" in t or "web" in t:
            url = self._extract_host(task) or "http://example.com"
            if not url.startswith("http"):
                url = "http://" + url
            return self._http_check(url)

        if "whois" in t:
            host = self._extract_host(task) or "google.com"
            return self._whois(host)

        if "ssl" in t or "cert" in t:
            host = self._extract_host(task) or "google.com"
            port = 443
            return self._ssl_check(host, port)

        if "ip" in t or "my ip" in t:
            return self._my_ip()

        if "speed" in t or "bandwidth" in t:
            return "NetworkAgent: Speed test requires speedtest-cli. Try: pip install speedtest-cli"

        return f"NetworkAgent: Available: ping <host>, scan [host], dns <host>, trace <host>, http <url>, whois <host>, ssl <host>, ip, speed"

    def _extract_host(self, task):
        for word in task.split():
            word = word.strip()
            if "." in word and not word.startswith("--"):
                return word
        return None

    def _ping(self, host):
        try:
            flag = "-n" if os.name == "nt" else "-c"
            result = subprocess.run(["ping", flag, "3", host], capture_output=True, text=True, timeout=15)
            lines = result.stdout.split("\n")
            summary = [l for l in lines if "time" in l.lower() or "ttl" in l.lower() or "avg" in l.lower() or "rtt" in l.lower()]
            return f"NetworkAgent: Ping {host}\n" + "\n".join(summary[:5])
        except Exception as e:
            return f"NetworkAgent: Ping failed: {e}"

    def _port_scan(self, host):
        open_ports = []
        common = [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 1433, 1521, 2049, 3306, 3389, 5432, 6379, 8080, 8443, 9090]
        for port in common:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.8)
                if s.connect_ex((host, port)) == 0:
                    service = self._port_name(port)
                    open_ports.append(f"{port}/{service}")
                s.close()
            except Exception:
                pass
        return f"NetworkAgent: Open ports on {host}: {', '.join(open_ports) if open_ports else 'none found'}"

    def _port_name(self, port):
        names = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
                 139: "NetBIOS", 143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
                 1433: "MSSQL", 1521: "Oracle", 2049: "NFS", 3306: "MySQL", 3389: "RDP",
                 5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt", 9090: "Prometheus"}
        return names.get(port, "unknown")

    def _dns_lookup(self, host):
        try:
            result = subprocess.run(["nslookup", host] if os.name == "nt" else ["dig", host, "+short"],
                                      capture_output=True, text=True, timeout=10)
            if result.stdout.strip():
                return f"NetworkAgent: DNS for {host}:\n{result.stdout.strip()[:500]}"
            ips = socket.gethostbyname_ex(host)
            return f"NetworkAgent: DNS for {host}: {ips[2]}"
        except Exception as e:
            return f"NetworkAgent: DNS failed: {e}"

    def _trace(self, host):
        try:
            cmd = ["tracert", host] if os.name == "nt" else ["traceroute", host]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            lines = result.stdout.split("\n")[:15]
            return f"NetworkAgent: Trace to {host}:\n" + "\n".join(lines)
        except Exception as e:
            return f"NetworkAgent: Trace failed: {e}"

    def _http_check(self, url):
        try:
            import requests
            start = time.time()
            r = requests.get(url, timeout=15, headers={"User-Agent": "WebOS/2.0"})
            elapsed = time.time() - start
            headers = dict(r.headers)
            return f"NetworkAgent: HTTP {url}\nStatus: {r.status_code}\nTime: {elapsed:.2f}s\nSize: {len(r.content)} bytes\nServer: {headers.get('Server', 'N/A')}\nContent-Type: {headers.get('Content-Type', 'N/A')}"
        except Exception as e:
            return f"NetworkAgent: HTTP failed: {e}"

    def _whois(self, host):
        try:
            import subprocess
            result = subprocess.run(["whois", host], capture_output=True, text=True, timeout=15)
            lines = result.stdout.split("\n")
            interesting = [l for l in lines if any(k in l.lower() for k in ["domain", "registrar", "creation", "expir", "name server", "org", "country"])]
            return f"NetworkAgent: Whois {host}:\n" + "\n".join(interesting[:10])
        except Exception as e:
            return f"NetworkAgent: Whois failed (whois may not be installed): {e}"

    def _ssl_check(self, host, port):
        try:
            import ssl
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
                s.settimeout(10)
                s.connect((host, port))
                cert = s.getpeercert()
                issuer = dict(x[0] for x in cert.get("issuer", []))
                subject = dict(x[0] for x in cert.get("subject", []))
                return f"NetworkAgent: SSL {host}:{port}\nIssuer: {issuer.get('organizationName', 'N/A')}\nSubject: {subject.get('commonName', 'N/A')}\nExpires: {cert.get('notAfter', 'N/A')}"
        except Exception as e:
            return f"NetworkAgent: SSL check failed: {e}"

    def _my_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local = s.getsockname()[0]
            s.close()
            import requests
            r = requests.get("https://api.ipify.org?format=json", timeout=5)
            public = r.json().get("ip", "unknown")
            return f"NetworkAgent: Local IP: {local}, Public IP: {public}"
        except Exception as e:
            return f"NetworkAgent: Could not determine IP: {e}"
