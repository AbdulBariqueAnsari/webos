"""
Web OS Plugin Example
This demonstrates the plugin system. Copy this file to the plugins/ directory
and it will be loaded automatically on next start.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.extensions.plugin_loader import Plugin
from agents.base_agent import BaseAgent


class HelloPlugin(Plugin):
    name = "hello_plugin"
    version = "1.0"
    description = "Example plugin that adds a greeting agent"
    author = "Web OS"

    def on_load(self, app, hub):
        # Register a new API route
        @app.route("/api/plugins/hello")
        def hello():
            return {"message": "Hello from plugin!"}

        # Register a new desktop icon handler
        print(f"[HelloPlugin] Plugin loaded! Route added: /api/plugins/hello")

    def get_agent(self):
        return HelloAgent()


class HelloAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "hello_agent",
            "A friendly agent that greets users and responds to simple questions",
        )
        self.capabilities = ["hello", "greet", "hi", "friend"]

    def run(self, task):
        self.add_memory(f"Task: {task}")
        t = task.lower()

        if "hello" in t or "hi" in t or "hey" in t:
            return "HelloAgent: 👋 Hello! Welcome to Web OS! How can I help you today?"

        if "how are you" in t:
            return "HelloAgent: I'm doing great! Thanks for asking. 😊"

        if "who are you" in t or "your name" in t:
            return "HelloAgent: I'm the Hello Plugin Agent for Web OS! I was loaded dynamically via the plugin system."

        if "plugin" in t:
            return "HelloAgent: Yes, I'm a plugin! The Web OS plugin system allows hot-reloadable extensions. Just drop a .py file in the plugins/ directory!"

        if "help" in t:
            return "HelloAgent: I understand: hello, how are you, who are you, plugin, help"

        return f"HelloAgent: You said: '{task}'. Try saying 'hello' or 'help'!"
