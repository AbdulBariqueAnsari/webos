import os, json, threading, time
from datetime import datetime
from agents.file_agent import FileAgent
from agents.network_agent import NetworkAgent
from agents.device_agent import DeviceAgent
from agents.data_agent import DataAgent
from agents.system_agent import SystemAgent
from agents.scheduler_agent import SchedulerAgent
from agents.code_agent import CodeAgent
from agents.image_agent import ImageAgent
from agents.search_agent import SearchAgent
from agents.chat_agent import ChatAgent
from agents.translator_agent import TranslatorAgent
from agents.math_agent import MathAgent
from agents.agent_memory import AgentMemory
from agents.agent_orchestrator import AgentOrchestrator
from server.database import db


class AgentHub:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.agents = {}
        self.conversation = []
        self._lock = threading.Lock()
        self.orchestrator = AgentOrchestrator()
        self.memory = AgentMemory("hub")
        self._register_defaults()

    def _register_defaults(self):
        for agent in [
            FileAgent(), NetworkAgent(), DeviceAgent(),
            DataAgent(), SystemAgent(), SchedulerAgent(),
            CodeAgent(), ImageAgent(), SearchAgent(),
            ChatAgent(), TranslatorAgent(), MathAgent(),
        ]:
            self.register(agent)

    def register(self, agent):
        if not hasattr(agent, 'version'):
            agent.version = "1.0"
        if not hasattr(agent, 'get_info'):
            agent.get_info = lambda a=agent: {"name": a.name, "version": getattr(a, 'version', '1.0')}
        self.agents[agent.name] = agent

    def list_agents(self):
        result = []
        for name, agent in self.agents.items():
            info = {"name": name}
            if hasattr(agent, 'get_info'):
                try:
                    info = agent.get_info()
                except Exception:
                    pass
            if hasattr(agent, 'capabilities'):
                info["capabilities"] = agent.capabilities
            mem = AgentMemory(name)
            stats = mem.get_stats()
            info["memory"] = {"conversations": stats["conversations"], "facts": stats["facts"]}
            result.append(info)
        return result

    def list_tasks(self):
        return db.query("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50")

    def run_agent(self, name, task):
        agent = self.agents.get(name)
        if not agent:
            available = list(self.agents.keys())
            return {"error": f"Agent '{name}' not found", "available": available}
        try:
            result = agent.run(task)
            self._log_conversation(name, task, result)
            db.execute(
                "INSERT INTO tasks (name, agent, task, result, status, completed_at) VALUES (?, ?, ?, ?, 'completed', datetime('now'))",
                (f"{name}: {task[:50]}", name, task, str(result)[:500]),
            )
            return {"agent": name, "result": result, "status": "completed"}
        except Exception as e:
            return {"agent": name, "error": str(e), "status": "error"}

    def process_message(self, message, mode="auto", session_id=None):
        msg_lower = message.lower()

        if mode == "broadcast":
            return self.broadcast(message)
        if mode == "chain":
            return self.chain(message)
        if mode == "plan":
            return self.plan_mode(message)

        route = self.orchestrator.route(message, "auto", session_id)
        primary = route.get("primary", "chat")
        supporting = route.get("supporting", [])

        agent = self.agents.get(primary)
        if agent:
            try:
                if hasattr(agent, 'process'):
                    result = agent.process(message, session_id or "default")
                else:
                    result_data = agent.run(message)
                    result = {"agent": primary, "response": str(result_data), "action": "run"}

                self._log_conversation(primary, message, result)
                db.execute(
                    "INSERT INTO tasks (name, agent, task, result, status, completed_at) VALUES (?, ?, ?, ?, 'completed', datetime('now'))",
                    (f"{primary}: {message[:50]}", primary, message, str(result)[:500]),
                )

                support_results = {}
                for s_name in supporting:
                    if s_name != primary:
                        s_agent = self.agents.get(s_name)
                        if s_agent:
                            try:
                                if hasattr(s_agent, 'process'):
                                    sr = s_agent.process(message, session_id or "default")
                                else:
                                    sr_data = s_agent.run(message)
                                    sr = {"agent": s_name, "response": str(sr_data)}
                                support_results[s_name] = sr.get("response", str(sr)[:200])
                            except Exception:
                                pass

                return {
                    "primary": result,
                    "supporting": support_results,
                    "route": route,
                    "session_id": session_id or "default"
                }
            except Exception as e:
                return {"primary": {"agent": primary, "error": str(e)}, "route": route}

        return self.broadcast(message)

    def broadcast(self, message):
        results = {}
        for name, agent in self.agents.items():
            try:
                if hasattr(agent, 'process'):
                    r = agent.process(message, "broadcast")
                else:
                    r_data = agent.run(message)
                    r = {"agent": name, "response": str(r_data)}
                results[name] = r.get("response", str(r)[:300])
            except Exception as e:
                results[name] = f"Error: {e}"
        self._log_conversation("broadcast", message, results)
        return {"mode": "broadcast", "results": results}

    def chain(self, message):
        results = []
        route = self.orchestrator.route(message, "chain")
        agents_list = route.get("agents", list(self.agents.keys())[:3])
        chain_msg = message
        for name in agents_list:
            agent = self.agents.get(name)
            if agent:
                try:
                    if hasattr(agent, 'process'):
                        r = agent.process(chain_msg, "chain")
                    else:
                        r_data = agent.run(chain_msg)
                        r = {"agent": name, "response": str(r_data)}
                    results.append({"agent": name, "result": r.get("response", str(r)[:300])})
                    chain_msg = f"Previous analysis: {r.get('response', '')[:200]}\n\nOriginal: {message}"
                except Exception as e:
                    results.append({"agent": name, "error": str(e)})
        self._log_conversation("chain", message, results)
        return {"mode": "chain", "steps": results}

    def plan_mode(self, message):
        route = self.orchestrator.route(message, "plan")
        plan = route.get("plan", [])
        results = []
        for step in plan:
            agent_name = step["agent"]
            agent = self.agents.get(agent_name)
            if agent:
                try:
                    if hasattr(agent, 'process'):
                        r = agent.process(f"{step['task']}: {message}", "plan")
                    else:
                        r_data = agent.run(message)
                        r = {"agent": agent_name, "response": str(r_data)}
                    results.append({"agent": agent_name, "task": step["task"], "result": r.get("response", str(r)[:200])})
                except Exception as e:
                    results.append({"agent": agent_name, "error": str(e)})
        return {"mode": "plan", "plan": plan, "results": results}

    def create_plan(self, goal):
        plan = {"goal": goal, "steps": [], "created": datetime.now().isoformat()}
        t = goal.lower()

        if "file" in t or "organize" in t or "backup" in t:
            plan["steps"].append({"agent": "file_agent", "task": goal, "priority": 1})
        if "network" in t or "scan" in t or "ping" in t:
            plan["steps"].append({"agent": "network_agent", "task": goal, "priority": 1})
        if "device" in t or "iot" in t:
            plan["steps"].append({"agent": "device_agent", "task": goal, "priority": 2})
        if "data" in t or "extract" in t or "report" in t:
            plan["steps"].append({"agent": "data_agent", "task": goal, "priority": 2})
        if "system" in t or "monitor" in t:
            plan["steps"].append({"agent": "system_agent", "task": goal, "priority": 3})
        if "schedule" in t or "every" in t:
            plan["steps"].append({"agent": "scheduler_agent", "task": goal, "priority": 1})
        if "code" in t or "program" in t or "script" in t or "debug" in t:
            plan["steps"].append({"agent": "code_agent", "task": goal, "priority": 1})
        if "image" in t or "picture" in t or "photo" in t:
            plan["steps"].append({"agent": "image_agent", "task": goal, "priority": 2})
        if "search" in t or "find" in t or "web" in t or "lookup" in t:
            plan["steps"].append({"agent": "search_agent", "task": goal, "priority": 1})
        if "translate" in t or "language" in t or "spanish" in t:
            plan["steps"].append({"agent": "translator_agent", "task": goal, "priority": 1})
        if "math" in t or "calculate" in t or "equation" in t:
            plan["steps"].append({"agent": "math_agent", "task": goal, "priority": 1})
        if "chat" in t or "hello" in t or "talk" in t:
            plan["steps"].append({"agent": "chat_agent", "task": goal, "priority": 1})

        if not plan["steps"]:
            plan["steps"].extend([
                {"agent": "system_agent", "task": f"Analyze system for: {goal}", "priority": 1},
                {"agent": "data_agent", "task": f"Gather data for: {goal}", "priority": 2},
                {"agent": "file_agent", "task": f"Prepare results for: {goal}", "priority": 3},
            ])

        return plan

    def _log_conversation(self, agent, task, result):
        with self._lock:
            self.conversation.append({
                "agent": agent, "task": task, "result": str(result)[:200],
                "time": datetime.now().isoformat(),
            })
            if len(self.conversation) > 200:
                self.conversation = self.conversation[-200:]

    def get_status(self):
        return {
            "agents": self.list_agents(),
            "orchestrator": self.orchestrator.get_agent_status(),
            "memory": self.memory.get_stats(),
            "total_conversations": len(self.conversation)
        }
