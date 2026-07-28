import os
import sys
import json
import asyncio
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CLIENTS = {}
CLIENTS_LOCK = threading.Lock()


GLOBAL_LOOP = None

class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=8084):
        self.host = host
        self.port = port
        self.server = None
        self.loop = None

    def start(self):
        asyncio.run(self._run())

    async def _run(self):
        global GLOBAL_LOOP
        self.loop = asyncio.get_running_loop()
        GLOBAL_LOOP = self.loop
        print(f"[WebSocket] Starting on ws://{self.host}:{self.port}")

        async def handler(reader, writer):
            client_id = f"client_{id(writer)}"
            addr = writer.get_extra_info("peername")
            print(f"[WebSocket] Client connected: {addr}")

            with CLIENTS_LOCK:
                CLIENTS[client_id] = {"writer": writer, "addr": addr, "connected": time.time()}

            try:
                while True:
                    data = await reader.read(4096)
                    if not data:
                        break
                    msg = data.decode("utf-8", errors="replace")
                    if msg.startswith("PING"):
                        writer.write(b"PONG\n")
                        await writer.drain()
                    elif msg.startswith("SUBSCRIBE:"):
                        channel = msg.split(":", 1)[1].strip()
                        with CLIENTS_LOCK:
                            CLIENTS[client_id]["channel"] = channel
            except Exception:
                pass
            finally:
                with CLIENTS_LOCK:
                    CLIENTS.pop(client_id, None)
                print(f"[WebSocket] Client disconnected: {addr}")

        self.server = await asyncio.start_server(handler, self.host, self.port)

        async def broadcast_task():
            while True:
                await asyncio.sleep(5)
                self._cleanup_clients()

        asyncio.create_task(broadcast_task())

        async with self.server:
            await self.server.serve_forever()

    def _cleanup_clients(self):
        dead = []
        with CLIENTS_LOCK:
            for cid, cinfo in CLIENTS.items():
                if cinfo.get("writer") and cinfo["writer"].is_closing():
                    dead.append(cid)
            for cid in dead:
                CLIENTS.pop(cid, None)

    def stop(self):
        if self.server:
            self.server.close()

    @staticmethod
    def broadcast(message, channel=None):
        msg_bytes = (json.dumps(message) + "\n").encode()
        with CLIENTS_LOCK:
            for cid, cinfo in list(CLIENTS.items()):
                try:
                    if channel and cinfo.get("channel") != channel:
                        continue
                    writer = cinfo.get("writer")
                    if writer and not writer.is_closing():
                        if GLOBAL_LOOP and GLOBAL_LOOP.is_running():
                            GLOBAL_LOOP.call_soon_threadsafe(writer.write, msg_bytes)
                        else:
                            writer.write(msg_bytes)
                except Exception:
                    pass

    @staticmethod
    def notify(title, message, ntype="info"):
        WebSocketServer.broadcast({
            "type": "notification",
            "title": title,
            "message": message,
            "ntype": ntype,
            "time": datetime.now().isoformat(),
        })


def start_ws_server(host="0.0.0.0", port=8084):
    server = WebSocketServer(host, port)
    server.start()
