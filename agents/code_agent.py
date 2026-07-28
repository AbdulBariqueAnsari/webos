import subprocess, tempfile, os, ast, sys, json, traceback, time
from agents.agent_memory import AgentMemory

class CodeAgent:
    def __init__(self):
        self.memory = AgentMemory("code")
        self.name = "code"
        self.capabilities = [
            "generate", "debug", "review", "explain", "refactor",
            "execute", "test", "format", "security_audit",
            "html", "css", "javascript", "python", "bash", "sql"
        ]

    def run(self, task):
        res = self.process(task)
        if isinstance(res, dict):
            return res.get("response", str(res))
        return str(res)

    def process(self, message, session_id="default"):
        self.memory.remember_conversation(session_id, "user", message)
        msg_lower = message.lower()

        result = None
        action = "analyze"

        if "execute" in msg_lower or "run" in msg_lower or ">>run" in message:
            result = self._execute_code(message)
            action = "execute"
        elif "debug" in msg_lower or "fix" in msg_lower or "error" in msg_lower:
            result = self._debug_code(message)
            action = "debug"
        elif "review" in msg_lower or "rate" in msg_lower:
            result = self._review_code(message)
            action = "review"
        elif "explain" in msg_lower or "what does" in msg_lower:
            result = self._explain_code(message)
            action = "explain"
        elif "security" in msg_lower or "vulnerable" in msg_lower:
            result = self._security_audit(message)
            action = "audit"
        elif "refactor" in msg_lower or "optimize" in msg_lower:
            result = self._refactor_code(message)
            action = "refactor"
        else:
            result = self._generate_code(message)
            action = "generate"

        if result:
            self.memory.remember_conversation(session_id, "assistant", str(result)[:1000])
            return {
                "agent": self.name,
                "action": action,
                "response": result.get("response", result.get("error", "Done")),
                "details": result
            }
        return {"agent": self.name, "action": "error", "response": "Kuch samajh nahi aaya"}

    def _extract_code(self, message):
        code_blocks = []
        lines = message.split("\n")
        in_block = False
        current = []
        lang = ""
        for line in lines:
            if line.strip().startswith("```"):
                if in_block:
                    code_blocks.append({"lang": lang, "code": "\n".join(current)})
                    current = []
                    lang = ""
                else:
                    lang = line.strip().strip("`").strip()
                in_block = not in_block
            elif in_block:
                current.append(line)
        if current:
            code_blocks.append({"lang": lang, "code": "\n".join(current)})
        return code_blocks if code_blocks else [{"lang": "", "code": message}]

    def _execute_code(self, message):
        blocks = self._extract_code(message)
        results = []
        for b in blocks:
            lang = b["lang"].lower() if b["lang"] else "python"
            code = b["code"]
            if not code.strip():
                continue
            try:
                if lang in ("python", "py"):
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                        f.write(code)
                        fname = f.name
                    try:
                        run = subprocess.run([sys.executable, fname], capture_output=True, text=True, timeout=15)
                        output = run.stdout + run.stderr
                        status = "success" if run.returncode == 0 else "error"
                    except subprocess.TimeoutExpired:
                        output = "[TIMEOUT] 15 seconds"
                        status = "timeout"
                    os.unlink(fname)
                elif lang in ("bash", "sh", "shell"):
                    run = subprocess.run(["bash", "-c", code], capture_output=True, text=True, timeout=15)
                    output = run.stdout + run.stderr
                    status = "success" if run.returncode == 0 else "error"
                elif lang in ("javascript", "js"):
                    try:
                        run = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=15)
                        output = run.stdout + run.stderr
                        status = "success" if run.returncode == 0 else "error"
                    except FileNotFoundError:
                        output = "Node.js not found on system"
                        status = "error"
                else:
                    output = f"Execution not supported for {lang}"
                    status = "skipped"
                results.append({"lang": lang, "status": status, "output": output[:2000]})
            except Exception as e:
                results.append({"lang": lang, "status": "error", "output": str(e)})
        response_parts = []
        for r in results:
            icon = {"success": "[OK]", "error": "[ERR]", "timeout": "[!]", "skipped": "[-]"}.get(r["status"], "[?]")
            response_parts.append(f"{icon} {r['lang']}: {r['output'][:300]}")
        return {"response": "\n".join(response_parts), "results": results}

    def _debug_code(self, message):
        blocks = self._extract_code(message)
        results = []
        for b in blocks:
            code = b["code"]
            if not code.strip():
                continue
            errors = []
            try:
                ast.parse(code)
                errors.append({"type": "syntax", "severity": "pass", "msg": "No syntax errors"})
            except SyntaxError as e:
                errors.append({"type": "syntax", "severity": "error", "msg": f"Line {e.lineno}: {e.msg}", "line": e.lineno})
            if "import " in code:
                for imp in re.findall(r"^import (\w+)|^from (\w+)", code, re.MULTILINE):
                    pkg = imp[0] or imp[1]
                    try:
                        __import__(pkg)
                    except ImportError:
                        errors.append({"type": "import", "severity": "warning", "msg": f"Module '{pkg}' not installed"})
            if "while True" in code and "break" not in code:
                errors.append({"type": "logic", "severity": "warning", "msg": "Infinite loop detected: while True without break"})
            results.append({"code_snippet": code[:100], "errors": errors})
        return {"response": json.dumps(results, indent=2), "results": results}

    def _review_code(self, message):
        blocks = self._extract_code(message)
        reviews = []
        for b in blocks:
            code = b["code"]
            score = 100
            issues = []
            if "print(" not in code and "return" not in code and len(code) > 50:
                issues.append("No output or return value")
                score -= 10
            if not code.strip().endswith("\n") and len(code) > 0:
                issues.append("No trailing newline")
                score -= 5
            if len(code.split("\n")) > 30 and "def " not in code:
                issues.append("Long script without functions")
                score -= 10
            if "try:" in code and "except:" in code:
                issues.append("Bare except clause")
                score -= 15
            if "#" not in code and len(code) > 200:
                issues.append("No comments")
                score -= 5
            docstring_count = code.count('"""') + code.count("'''")
            if docstring_count < 2 and len(code) > 100:
                issues.append("Missing docstrings")
                score -= 5
            type_hints = [l for l in code.split("\n") if "def " in l and ":" in l.split("def")[-1]]
            if not type_hints and len(code) > 100:
                issues.append("No type hints")
                score -= 5
            score = max(0, min(100, score))
            reviews.append({"score": score, "issues": issues, "verdict": "Good" if score >= 70 else "Needs improvement"})
        avg_score = sum(r["score"] for r in reviews) / len(reviews) if reviews else 0
        return {"response": f"Review score: {avg_score:.0f}/100", "reviews": reviews}

    def _explain_code(self, message):
        blocks = self._extract_code(message)
        explanations = []
        for b in blocks:
            code = b["code"]
            try:
                tree = ast.parse(code)
                imports = []
                functions = []
                classes = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        imports.append(f"{node.module}.{node.names[0].name}" if node.names else node.module or "")
                    elif isinstance(node, ast.FunctionDef):
                        functions.append(node.name)
                    elif isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                explanations.append({
                    "imports": imports, "functions": functions,
                    "classes": classes, "lines": len(code.split("\n"))
                })
            except SyntaxError as e:
                explanations.append({"error": str(e)})
        return {"response": json.dumps(explanations, indent=2), "explanations": explanations}

    def _security_audit(self, message):
        blocks = self._extract_code(message)
        findings = []
        for b in blocks:
            code = b["code"]
            vulns = []
            if "eval(" in code or "exec(" in code:
                vulns.append({"severity": "high", "msg": "eval/exec usage - code injection risk"})
            if "subprocess." in code and "shell=True" in code:
                vulns.append({"severity": "high", "msg": "shell=True - command injection risk"})
            if "pickle.load" in code:
                vulns.append({"severity": "medium", "msg": "pickle.load - deserialization risk"})
            if "os.system(" in code or "os.popen(" in code:
                vulns.append({"severity": "medium", "msg": "os.system/popen - use subprocess instead"})
            if "input(" in code:
                vulns.append({"severity": "low", "msg": "input() in Python 2 is dangerous"})
            if "sql" in code.lower() and "+" in code and ("SELECT" in code.upper() or "INSERT" in code.upper()):
                vulns.append({"severity": "high", "msg": "SQL string concatenation - injection risk"})
            findings.append({"code_snippet": code[:80], "vulnerabilities": vulns})
        vuln_count = sum(len(f["vulnerabilities"]) for f in findings)
        return {"response": f"Found {vuln_count} issue(s)", "findings": findings}

    def _refactor_code(self, message):
        blocks = self._extract_code(message)
        refactored = []
        for b in blocks:
            code = b["code"]
            lines = code.split("\n")
            suggestions = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                if len(stripped) > 120:
                    suggestions.append(f"Line {i+1} too long ({len(stripped)} chars)")
            if len(lines) > 50 and "def " not in code:
                suggestions.append("Consider splitting into functions")
            repeat_blocks = {}
            for i in range(len(lines) - 2):
                block = "\n".join(lines[i:i+3])
                if block in repeat_blocks:
                    repeat_blocks[block].append(i)
                else:
                    repeat_blocks[block] = [i]
            for block, positions in repeat_blocks.items():
                if len(positions) > 1:
                    suggestions.append(f"Duplicated code at lines {positions[0]+1}, {positions[1]+1}")
                    break
            refactored.append({"suggestions": suggestions, "count": len(suggestions)})
        return {"response": json.dumps(refactored, indent=2), "refactored": refactored}

    def _generate_code(self, message):
        msg_lower = message.lower()
        if "python" in msg_lower or "py" in msg_lower.split():
            lang = "python"
        elif "html" in msg_lower:
            lang = "html"
        elif "css" in msg_lower:
            lang = "css"
        elif "javascript" in msg_lower or "js" in msg_lower.split():
            lang = "javascript"
        elif "bash" in msg_lower or "shell" in msg_lower:
            lang = "bash"
        elif "sql" in msg_lower:
            lang = "sql"
        else:
            lang = "python"

        if "calculate" in msg_lower or "add" in msg_lower or "sum" in msg_lower:
            code = self._generate_calculator(message, lang)
        elif "web" in msg_lower or "server" in msg_lower:
            code = self._generate_web_server(lang)
        elif "sort" in msg_lower or "search" in msg_lower:
            code = self._generate_algorithm(message, lang)
        else:
            code = f"# {lang} code for: {message[:50]}\n# Provide more details for specific implementation\n"

        return {"response": f"```{lang}\n{code}\n```", "code": code, "lang": lang}

    def _generate_calculator(self, message, lang):
        snippets = {
            "python": "def calculate(a, b, op):\n    ops = {'+': lambda x,y: x+y, '-': lambda x,y: x-y, '*': lambda x,y: x*y, '/': lambda x,y: x/y}\n    return ops.get(op, lambda x,y: None)(a, b)",
            "javascript": "function calculate(a, b, op) {\n  const ops = {'+': (x,y)=>x+y, '-': (x,y)=>x-y, '*': (x,y)=>x*y, '/': (x,y)=>x/y};\n  return ops[op]?.(a, b);\n}"
        }
        return snippets.get(lang, snippets["python"])

    def _generate_web_server(self, lang):
        snippets = {
            "python": "from flask import Flask\napp = Flask(__name__)\n@app.route('/')\ndef home():\n    return 'Hello World'\nif __name__ == '__main__':\n    app.run(port=8080)",
            "javascript": "const http = require('http');\nhttp.createServer((req, res) => {\n  res.writeHead(200);\n  res.end('Hello World');\n}).listen(8080);",
            "html": "<!DOCTYPE html>\n<html>\n<head><title>Page</title></head>\n<body><h1>Hello World</h1></body>\n</html>"
        }
        return snippets.get(lang, snippets["python"])

    def _generate_algorithm(self, message, lang):
        if "sort" in message.lower():
            snippets = {
                "python": "def quick_sort(arr):\n    if len(arr) <= 1: return arr\n    pivot = arr[len(arr)//2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)",
                "javascript": "function quickSort(arr) {\n  if (arr.length <= 1) return arr;\n  const pivot = arr[Math.floor(arr.length/2)];\n  const left = arr.filter(x => x < pivot);\n  const middle = arr.filter(x => x === pivot);\n  const right = arr.filter(x => x > pivot);\n  return [...quickSort(left), ...middle, ...quickSort(right)];\n}"
            }
        elif "search" in message.lower():
            snippets = {
                "python": "def binary_search(arr, target):\n    low, high = 0, len(arr)-1\n    while low <= high:\n        mid = (low+high)//2\n        if arr[mid] == target: return mid\n        elif arr[mid] < target: low = mid+1\n        else: high = mid-1\n    return -1"
            }
        else:
            snippets = {"python": "# Algorithm placeholder\npass"}
        return snippets.get(lang, snippets.get("python", ""))

    def get_status(self):
        return {"name": self.name, "capabilities": self.capabilities, "memory": self.memory.get_stats()}

import re
