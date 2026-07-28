import os, json, subprocess, tempfile, textwrap, sys, traceback


class CodeRunner:
    def __init__(self):
        self.sandbox_dir = tempfile.mkdtemp(prefix="webos_sandbox_")

    def run_python(self, code, timeout=10):
        """Run Python code in a subprocess with timeout."""
        fpath = os.path.join(self.sandbox_dir, "_temp_script.py")
        try:
            with open(fpath, "w") as f:
                f.write(textwrap.dedent(code))
            r = subprocess.run(
                [sys.executable, fpath],
                capture_output=True, text=True, timeout=timeout,
                cwd=self.sandbox_dir,
            )
            result = {
                "status": "ok",
                "stdout": r.stdout,
                "stderr": r.stderr,
                "returncode": r.returncode,
            }
        except subprocess.TimeoutExpired:
            result = {"status": "error", "stdout": "", "stderr": "Execution timed out", "returncode": -1}
        except Exception as e:
            result = {"status": "error", "stdout": "", "stderr": str(e), "returncode": -1}
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)
        return result

    def run_javascript(self, code, timeout=10):
        """Run JavaScript code via Node.js if available."""
        try:
            r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                return {"status": "error", "stdout": "", "stderr": "Node.js not available", "returncode": -1}
        except Exception:
            return {"status": "error", "stdout": "", "stderr": "Node.js not available", "returncode": -1}

        fpath = os.path.join(self.sandbox_dir, "_temp_script.js")
        try:
            with open(fpath, "w") as f:
                f.write(code)
            r = subprocess.run(
                ["node", fpath],
                capture_output=True, text=True, timeout=timeout,
                cwd=self.sandbox_dir,
            )
            result = {
                "status": "ok",
                "stdout": r.stdout,
                "stderr": r.stderr,
                "returncode": r.returncode,
            }
        except subprocess.TimeoutExpired:
            result = {"status": "error", "stdout": "", "stderr": "Execution timed out", "returncode": -1}
        except Exception as e:
            result = {"status": "error", "stdout": "", "stderr": str(e), "returncode": -1}
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)
        return result

    def run_shell(self, cmd, timeout=10):
        """Run shell command."""
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return {
                "status": "ok",
                "stdout": r.stdout,
                "stderr": r.stderr,
                "returncode": r.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "stdout": "", "stderr": "Command timed out", "returncode": -1}
        except Exception as e:
            return {"status": "error", "stdout": "", "stderr": str(e), "returncode": -1}


code_runner = CodeRunner()
