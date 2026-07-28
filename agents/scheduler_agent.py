import os, json, threading, time
from datetime import datetime
from agents.base_agent import BaseAgent


class SchedulerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "scheduler_agent",
            "Schedule recurring tasks, reminders, and automated operations",
        )
        self.capabilities = ["schedule", "task", "cron", "timer", "reminder", "recurring", "automate"]
        self.scheduled_tasks = []
        self._running = True
        self._worker = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._worker.start()

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()

        if "list" in t or "tasks" in t:
            if not self.scheduled_tasks:
                return "SchedulerAgent: No scheduled tasks"
            lines = ["Scheduled Tasks:"]
            for s in self.scheduled_tasks:
                lines.append(f"  [{s['id']}] {s['name']}: every {s['interval']}s (next: {s['next_run']})")
            return "\n".join(lines)

        if "add" in t or "create" in t or "schedule" in t:
            import re
            nums = re.findall(r'\d+', t)
            interval = int(nums[0]) if nums else 60
            name = "task_" + str(len(self.scheduled_tasks) + 1)
            action = task.split("run")[-1].strip() if "run" in t else task
            return self._add_task(name, interval, action)

        if "remove" in t or "delete" in t:
            import re
            nums = re.findall(r'\d+', t)
            tid = int(nums[0]) if nums else None
            if tid:
                self.scheduled_tasks = [s for s in self.scheduled_tasks if s["id"] != tid]
                return f"SchedulerAgent: Removed task {tid}"
            return "SchedulerAgent: Usage: remove <task_id>"

        if "clean" in t:
            count = len(self.scheduled_tasks)
            self.scheduled_tasks = []
            return f"SchedulerAgent: Removed all {count} tasks"

        return f"SchedulerAgent: Available: list, add <interval>s run <action>, remove <id>, clean"

    def _add_task(self, name, interval, action):
        from agents.agent_manager_hub import AgentHub
        task_id = len(self.scheduled_tasks) + 1
        task = {
            "id": task_id,
            "name": name,
            "interval": interval,
            "action": action,
            "next_run": time.time() + interval,
            "created": datetime.now().isoformat(),
        }
        self.scheduled_tasks.append(task)
        return f"SchedulerAgent: Scheduled '{name}' every {interval}s (ID: {task_id})"

    def _scheduler_loop(self):
        while self._running:
            now = time.time()
            for task in self.scheduled_tasks:
                if now >= task["next_run"]:
                    task["next_run"] = now + task["interval"]
                    try:
                        from agents.agent_manager_hub import AgentHub
                        hub = AgentHub()
                        result = hub.process_message(task["action"])
                        print(f"[Scheduler] Ran '{task['name']}': {str(result)[:100]}")
                    except Exception as e:
                        print(f"[Scheduler] Error: {e}")
            time.sleep(5)

    def stop(self):
        self._running = False
