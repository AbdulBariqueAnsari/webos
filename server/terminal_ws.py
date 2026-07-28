import os, select, struct, signal, threading
try:
    import pty, fcntl, termios
    HAS_PTY = True
except ImportError:
    pty = fcntl = termios = None
    HAS_PTY = False
from flask import request
from server.auth import validate_token

class TerminalWS:
    _sessions = {}

    @classmethod
    def handle(cls, ws, path):
        token = request.args.get("token", "")
        if not validate_token(token):
            ws.close(4001, "Unauthorized")
            return

        import queue
        session_id = id(ws)
        log_lines = []
        buffer = queue.Queue()

        def write_output(data):
            if isinstance(data, str):
                data = data.encode("utf-8", errors="replace")
            buffer.put(data)

        def run_shell():
            if not HAS_PTY:
                ws.send(b"PTY terminal not supported on Windows platform\r\n")
                return
            pid, fd = pty.fork()
            if pid == 0:
                os.setsid()
                for sig in [signal.SIGINT, signal.SIGQUIT, signal.SIGTERM]:
                    signal.signal(sig, signal.SIG_DFL)
                os.environ["TERM"] = "xterm-256color"
                os.environ["SHELL"] = "/bin/bash"
                os.execve("/bin/bash", ["/bin/bash", "--login"], os.environ)
            else:
                cls._sessions[session_id] = {"pid": pid, "fd": fd}
                try:
                    while True:
                        r, w, e = select.select([fd], [], [], 0.05)
                        if r:
                            try:
                                data = os.read(fd, 4096)
                                if not data:
                                    break
                                log_lines.append(data.decode("utf-8", errors="replace"))
                                if len(log_lines) > 5000:
                                    log_lines[:1000]
                                ws.send(data)
                            except OSError:
                                break
                except Exception:
                    pass
                finally:
                    try:
                        os.close(fd)
                        os.waitpid(pid, 0)
                    except Exception:
                        pass
                    cls._sessions.pop(session_id, None)

        shell_thread = threading.Thread(target=run_shell, daemon=True)
        shell_thread.start()

        try:
            while True:
                data = ws.receive()
                if data is None:
                    break
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                fd_info = cls._sessions.get(session_id)
                if fd_info:
                    fd = fd_info["fd"]
                    if data == "RESIZE":
                        try:
                            cols = int(request.args.get("cols", 80))
                            rows = int(request.args.get("rows", 24))
                            winsize = struct.pack("HHHH", rows, cols, 0, 0)
                            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
                        except Exception:
                            pass
                    else:
                        try:
                            os.write(fd, data.encode("utf-8"))
                        except OSError:
                            break
        except Exception:
            pass
        finally:
            fd_info = cls._sessions.pop(session_id, None)
            if fd_info:
                try:
                    os.close(fd_info["fd"])
                    os.waitpid(fd_info["pid"], 0)
                except Exception:
                    pass
