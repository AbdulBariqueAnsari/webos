#!/usr/bin/env python3
"""
Web OS v1.0 — Native Graphical Desktop Control Center & GUI Launcher
Provides a complete 100% Graphical User Interface (GUI) for Web OS.
"""

import os
import sys
import time
import socket
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *
import main as main_backend

class WebOSGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Web OS v1.0 — Graphical Desktop Control Center")
        self.root.geometry("900x650")
        self.root.minsize(800, 550)

        # Styling & Colors
        self.bg_color = "#0f0f1b"
        self.card_bg = "#1a1a2e"
        self.card_border = "#2a2a50"
        self.primary_color = "#7c6bff"
        self.accent_color = "#00b894"
        self.text_color = "#e8e8f0"
        self.text_muted = "#a0a0c0"

        self.root.configure(bg=self.bg_color)
        
        self.primary_ip, self.all_ips = main_backend.get_all_ips()
        self.host_name = socket.gethostname()
        self.desktop_url = f"http://localhost:{HTTP_PORT}/desktop"
        self.lan_url = f"http://{self.primary_ip}:{HTTP_PORT}"

        self.build_ui()
        self.start_servers()

        # Auto open browser after 1.5s
        self.root.after(1500, self.auto_open_browser)
        self.root.after(2000, self.update_system_stats)

    def build_ui(self):
        # Header Frame
        header = tk.Frame(self.root, bg=self.card_bg, highlightbackground=self.card_border, highlightthickness=1)
        header.pack(fill=tk.X, padx=16, pady=(16, 10))

        title_lbl = tk.Label(
            header, 
            text="🌐 Web OS v1.0 Ultimate", 
            font=("Segoe UI", 18, "bold"), 
            bg=self.card_bg, 
            fg=self.primary_color
        )
        title_lbl.pack(side=tk.LEFT, padx=16, pady=12)

        status_lbl = tk.Label(
            header, 
            text="● ONLINE", 
            font=("Segoe UI", 10, "bold"), 
            bg=self.card_bg, 
            fg=self.accent_color
        )
        status_lbl.pack(side=tk.RIGHT, padx=16, pady=12)

        ip_lbl = tk.Label(
            header, 
            text=f"Primary LAN: {self.lan_url}  |  Host: {self.host_name}", 
            font=("Segoe UI", 9), 
            bg=self.card_bg, 
            fg=self.text_muted
        )
        ip_lbl.pack(side=tk.RIGHT, padx=10, pady=12)

        # Action Buttons Toolbar
        toolbar = tk.Frame(self.root, bg=self.bg_color)
        toolbar.pack(fill=tk.X, padx=16, pady=6)

        btn_open = tk.Button(
            toolbar, 
            text="🚀 Launch Web OS Desktop", 
            command=self.auto_open_browser, 
            font=("Segoe UI", 10, "bold"), 
            bg=self.accent_color, 
            fg="#ffffff", 
            activebackground="#00a383", 
            activeforeground="#ffffff", 
            relief=tk.FLAT, 
            padx=14, 
            pady=8, 
            cursor="hand2"
        )
        btn_open.pack(side=tk.LEFT, padx=(0, 8))

        btn_copy = tk.Button(
            toolbar, 
            text="📋 Copy LAN URL", 
            command=self.copy_lan_url, 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_color, 
            activebackground=self.primary_color, 
            activeforeground="#ffffff", 
            relief=tk.FLAT, 
            padx=12, 
            pady=8, 
            cursor="hand2"
        )
        btn_copy.pack(side=tk.LEFT, padx=4)

        btn_net = tk.Button(
            toolbar, 
            text="📶 Network Info", 
            command=self.show_network_dialog, 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_color, 
            activebackground=self.primary_color, 
            activeforeground="#ffffff", 
            relief=tk.FLAT, 
            padx=12, 
            pady=8, 
            cursor="hand2"
        )
        btn_net.pack(side=tk.LEFT, padx=4)

        btn_restart = tk.Button(
            toolbar, 
            text="🔄 Restart", 
            command=self.restart_servers, 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_color, 
            relief=tk.FLAT, 
            padx=12, 
            pady=8, 
            cursor="hand2"
        )
        btn_restart.pack(side=tk.LEFT, padx=4)

        btn_exit = tk.Button(
            toolbar, 
            text="🛑 Shutdown", 
            command=self.on_close, 
            font=("Segoe UI", 9, "bold"), 
            bg="#ff4757", 
            fg="#ffffff", 
            relief=tk.FLAT, 
            padx=12, 
            pady=8, 
            cursor="hand2"
        )
        btn_exit.pack(side=tk.RIGHT)

        # Server Status Cards Grid
        grid_frame = tk.Frame(self.root, bg=self.bg_color)
        grid_frame.pack(fill=tk.X, padx=16, pady=8)

        self.cards = {}
        services_info = [
            ("HTTP Server", f"Port {HTTP_PORT}", f"http://localhost:{HTTP_PORT}"),
            ("WebDAV Server", f"Port {WEBDAV_PORT}", f"http://localhost:{WEBDAV_PORT}"),
            ("File Server", f"Port {FILE_PORT}", f"http://localhost:{FILE_PORT}"),
            ("WebSocket", f"Port {WS_PORT}", f"ws://localhost:{WS_PORT}"),
        ]

        for i, (name, sub, link) in enumerate(services_info):
            card = tk.Frame(grid_frame, bg=self.card_bg, highlightbackground=self.card_border, highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=4, pady=4)
            grid_frame.columnconfigure(i, weight=1)

            c_name = tk.Label(card, text=name, font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.text_color)
            c_name.pack(anchor="w", padx=10, pady=(8, 2))

            c_sub = tk.Label(card, text=sub, font=("Segoe UI", 8), bg=self.card_bg, fg=self.text_muted)
            c_sub.pack(anchor="w", padx=10, pady=(0, 8))

            c_status = tk.Label(card, text="● ACTIVE", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg=self.accent_color)
            c_status.pack(anchor="w", padx=10, pady=(0, 8))

            self.cards[name] = c_status

        # Live Console Output Feed
        log_frame = tk.Frame(self.root, bg=self.card_bg, highlightbackground=self.card_border, highlightthickness=1)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 16))

        log_title = tk.Label(log_frame, text="🖥️ Live Server & Network Log Monitor", font=("Segoe UI", 10, "bold"), bg=self.card_bg, fg=self.primary_color)
        log_title.pack(anchor="w", padx=12, pady=(10, 4))

        self.log_area = scrolledtext.ScrolledText(
            log_frame, 
            bg="#0a0a14", 
            fg="#2ecc71", 
            font=("Consolas", 9), 
            relief=tk.FLAT, 
            insertbackground="#ffffff"
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.log(f"[{time.strftime('%H:%M:%S')}] Web OS GUI Control Center initialized.")
        self.log(f"[{time.strftime('%H:%M:%S')}] Hostname: {self.host_name} | Primary LAN IP: {self.primary_ip}")
        self.log(f"[{time.strftime('%H:%M:%S')}] Detected IP Addresses: {', '.join(self.all_ips)}")
        self.log(f"[{time.strftime('%H:%M:%S')}] HTTP Server -> http://localhost:{HTTP_PORT}")
        self.log(f"[{time.strftime('%H:%M:%S')}] Web OS Desktop UI -> http://localhost:{HTTP_PORT}/desktop")

    def log(self, text):
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)

    def start_servers(self):
        services = [
            ("HTTP", main_backend.start_http, AUTO_START_SERVERS.get("http", True)),
            ("WebDAV", main_backend.start_webdav, AUTO_START_SERVERS.get("webdav", True)),
            ("File", main_backend.start_file, AUTO_START_SERVERS.get("file", True)),
            ("WebSocket", main_backend.start_ws, AUTO_START_SERVERS.get("websocket", True)),
        ]

        self.server_threads = {}
        for name, fn, enabled in services:
            if enabled:
                t = main_backend.ServerThread(target=fn, name=name)
                t.start()
                self.server_threads[name] = t
                time.sleep(0.2)
                self.log(f"[{time.strftime('%H:%M:%S')}] [OK] Started {name} Server daemon thread.")

    def auto_open_browser(self):
        url = f"http://localhost:{HTTP_PORT}/desktop"
        self.log(f"[{time.strftime('%H:%M:%S')}] Opening Web OS Desktop UI in browser: {url}")
        
        # Try chrome app mode first
        try:
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            ]
            launched = False
            for p in chrome_paths:
                if os.path.exists(p):
                    subprocess.Popen([p, f"--app={url}"])
                    launched = True
                    break
            if not launched:
                webbrowser.open(url)
        except Exception:
            webbrowser.open(url)

    def copy_lan_url(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.lan_url)
        messagebox.showinfo("Copied!", f"Primary LAN Access URL copied to clipboard:\n\n{self.lan_url}")

    def show_network_dialog(self):
        info_win = tk.Toplevel(self.root)
        info_win.title("Network Interfaces & IP Details")
        info_win.geometry("550x400")
        info_win.configure(bg=self.bg_color)

        title = tk.Label(info_win, text="📶 Network Adapters & IP Addresses", font=("Segoe UI", 12, "bold"), bg=self.bg_color, fg=self.primary_color)
        title.pack(anchor="w", padx=16, pady=12)

        st = scrolledtext.ScrolledText(info_win, bg=self.card_bg, fg=self.text_color, font=("Consolas", 9), relief=tk.FLAT)
        st.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        try:
            import psutil
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            st.insert(tk.END, f"Host Name: {self.host_name}\nPrimary IP: {self.primary_ip}\n{'='*50}\n\n")
            for name, addr_list in addrs.items():
                s = stats.get(name)
                is_up = "ACTIVE" if (s and s.isup) else "DOWN"
                st.insert(tk.END, f"Adapter: {name} [{is_up}]\n")
                for a in addr_list:
                    if a.family == socket.AF_INET:
                        st.insert(tk.END, f"  - IPv4: {a.address} (Netmask: {a.netmask})\n")
                    elif hasattr(socket, 'AF_INET6') and a.family == socket.AF_INET6:
                        st.insert(tk.END, f"  - IPv6: {a.address.split('%')[0]}\n")
                    elif hasattr(psutil, 'AF_LINK') and a.family == psutil.AF_LINK:
                        st.insert(tk.END, f"  - MAC : {a.address}\n")
                st.insert(tk.END, "\n")
        except Exception as e:
            st.insert(tk.END, f"Error retrieving network interfaces: {e}")

    def update_system_stats(self):
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            now = time.strftime("%H:%M:%S")
            self.log(f"[{now}] [SYSTEM HEARTBEAT] CPU: {cpu}% | Memory: {mem}% | Server Status: Healthy")
        except Exception:
            pass
        self.root.after(10000, self.update_system_stats)

    def restart_servers(self):
        self.log(f"[{time.strftime('%H:%M:%S')}] Restarting servers...")
        self.start_servers()
        messagebox.showinfo("Restart", "Web OS Servers restarted successfully!")

    def on_close(self):
        if messagebox.askokcancel("Shutdown", "Shutdown Web OS servers and exit GUI?"):
            self.root.destroy()
            sys.exit(0)

def launch():
    root = tk.Tk()
    app = WebOSGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    launch()
