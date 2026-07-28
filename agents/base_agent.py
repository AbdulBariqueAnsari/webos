from datetime import datetime


class BaseAgent:
    def __init__(self, name, description="", version="1.0"):
        self.name = name
        self.description = description
        self.version = version
        self.memory = []
        self.capabilities = []
        self.running = False
        self._task_count = 0

    def run(self, task):
        raise NotImplementedError

    def get_info(self):
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities,
            "memory_size": len(self.memory),
            "task_count": self._task_count,
        }

    def add_memory(self, item):
        self.memory.append({"time": datetime.now().isoformat(), "item": item})
        if len(self.memory) > 200:
            self.memory = self.memory[-200:]
        self._task_count += 1

    def can_handle(self, task):
        task_lower = task.lower()
        for cap in self.capabilities:
            if cap.lower() in task_lower:
                return True
        return False
