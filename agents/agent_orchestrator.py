import time, json, re, random
from agents.agent_memory import AgentMemory
from collections import OrderedDict

class AgentOrchestrator:
    def __init__(self):
        self.memory = AgentMemory("orchestrator")
        self.routing_rules = OrderedDict()
        self._init_rules()
        self.conversation_context = {}

    def _init_rules(self):
        rules = [
            ("file", ["file", "folder", "directory", "save", "load", "read", "write", "copy", "move", "delete", "rename", "list", "find", "search file", "ls", "cat", "mkdir", "touch", "permission"]),
            ("network", ["network", "internet", "wifi", "ethernet", "ip", "dns", "ping", "connect", "download", "upload", "speed", "bandwidth", "ssh", "ftp", "http", "url", "curl"]),
            ("device", ["device", "usb", "bluetooth", "printer", "scanner", "mouse", "keyboard", "driver", "hardware", "monitor", "screen", "display", "resolution", "sensor"]),
            ("data", ["data", "database", "json", "csv", "xml", "export", "import", "backup", "sync", "query", "sql", "table", "record", "entry"]),
            ("system", ["system", "cpu", "ram", "memory", "disk", "process", "service", "kernel", "os", "update", "upgrade", "package", "install", "config", "setting", "log"]),
            ("scheduler", ["schedule", "cron", "timer", "remind", "recurring", "daily", "weekly", "job", "task", "plan", "alarm", "notification"]),
            ("code", ["code", "program", "function", "script", "bug", "debug", "compile", "syntax", "algorithm", "python", "javascript", "html", "css", "api", "class", "method", "variable"]),
            ("image", ["image", "photo", "picture", "png", "jpg", "gif", "svg", "thumbnail", "resize", "crop", "convert", "exif", "metadata", "draw", "render", "logo", "icon"]),
            ("search", ["search", "google", "wikipedia", "duckduckgo", "web", "find online", "lookup", "query", "information about", "what is", "who is", "define"]),
            ("chat", ["chat", "hello", "hi", "hey", "how are you", "thanks", "thank", "bye", "goodbye", "joke", "quote", "motivate", "help", "who are you", "what can you do"]),
            ("translator", ["translate", "language", "urdu", "hindi", "english", "spanish", "french", "german", "arabic", "chinese", "japanese", "convert language"]),
            ("math", ["math", "calculate", "equation", "formula", "prime", "factorial", "fibonacci", "sqrt", "power", "percentage", "gcd", "lcm", "solve", "number"]),
        ]
        for agent, keywords in rules:
            self.routing_rules[agent] = keywords

    def analyze_query(self, query):
        query_lower = query.lower()
        scores = {}
        for agent, keywords in self.routing_rules.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[agent] = score
        return OrderedDict(sorted(scores.items(), key=lambda x: -x[1]))

    def route(self, query, mode="auto", session_id=None):
        if session_id:
            ctx = self.conversation_context.get(session_id, {})
        else:
            ctx = {}

        if mode == "broadcast":
            return {"mode": "broadcast", "agents": list(self.routing_rules.keys())}

        if mode == "chain":
            scored = self.analyze_query(query)
            top_agents = list(scored.keys())[:3] if scored else ["chat"]
            return {"mode": "chain", "agents": top_agents}

        if mode == "plan":
            scored = self.analyze_query(query)
            plan = self._create_plan(query, scored, ctx)
            return {"mode": "plan", "plan": plan}

        scored = self.analyze_query(query)
        if scored:
            primary = list(scored.keys())[0]
            supporting = list(scored.keys())[1:3]
        else:
            primary = "chat"
            supporting = ["search"]

        context_suggestions = []
        if ctx.get("last_agent"):
            context_suggestions.append(ctx["last_agent"])

        if session_id:
            if session_id not in self.conversation_context:
                self.conversation_context[session_id] = {"turn": 0, "last_agent": None}
            self.conversation_context[session_id]["turn"] += 1
            self.conversation_context[session_id]["last_agent"] = primary

        return {
            "mode": "auto",
            "primary": primary,
            "supporting": supporting,
            "confidence": scored[primary] / max(scored.values()) if scored else 0.5,
            "context": context_suggestions
        }

    def _create_plan(self, query, scores, ctx):
        plan = []
        if "code" in scores:
            plan.append({"agent": "code", "task": "analyze or generate code", "deps": []})
        if "search" in scores:
            plan.append({"agent": "search", "task": "search for information", "deps": []})
        if "translator" in scores:
            plan.append({"agent": "translator", "task": "translate text", "deps": []})
        if "math" in scores:
            plan.append({"agent": "math", "task": "perform calculations", "deps": []})
        if "file" in scores:
            plan.append({"agent": "file", "task": "manage files", "deps": []})
        if "system" in scores:
            plan.append({"agent": "system", "task": "system operations", "deps": []})
        if "image" in scores:
            plan.append({"agent": "image", "task": "image processing", "deps": []})
        if not plan:
            plan.append({"agent": "chat", "task": "general conversation", "deps": []})
        return plan

    def execute_plan(self, plan, query, session_id):
        results = []
        completed = set()
        for step in plan:
            agent = step["agent"]
            deps = step.get("deps", [])
            dep_results = [r for r in results if r["agent"] in deps]
            step_result = {
                "agent": agent,
                "task": step["task"],
                "status": "pending",
                "result": None,
                "dependencies_met": all(d in completed for d in deps)
            }
            results.append(step_result)
            completed.add(agent)
        return results

    def get_conversation_summary(self, session_id):
        mem = AgentMemory("orchestrator")
        convs = mem.recall_conversation(session_id, 20)
        if not convs:
            return "No prior conversation"
        summary = []
        for c in convs[-5:]:
            content = c["content"][:100]
            summary.append(f"{c['role']}: {content}")
        return "\n".join(summary)

    def get_agent_status(self):
        mem = AgentMemory("orchestrator")
        stats = mem.get_stats()
        agents = []
        for name in self.routing_rules:
            agent_mem = AgentMemory(name)
            s = agent_mem.get_stats()
            agents.append({"name": name, "conversations": s["conversations"], "facts": s["facts"]})
        return {"orchestrator": stats, "agents": agents}
