import os, json, re, random
from datetime import datetime
from agents.base_agent import BaseAgent

class ChatAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "chat_agent",
            "Conversational AI assistant for general questions, advice, and casual conversation",
        )
        self.capabilities = ["chat", "talk", "conversation", "hello", "hi", "help", "advice", "question"]
        self.responses = {
            "greeting": [
                "Hello! How can I assist you today?",
                "Hi there! I'm the Web OS Chat Agent. What can I help you with?",
                "Greetings! I'm ready to help with any questions.",
                "Hey! How's it going? I'm here to help.",
            ],
            "farewell": [
                "Goodbye! Have a great day!",
                "See you later! Feel free to come back anytime.",
                "Take care! I'll be here if you need me.",
            ],
            "thanks": [
                "You're welcome! Happy to help.",
                "My pleasure! Let me know if you need anything else.",
                "Anytime! That's what I'm here for.",
            ],
            "help": [
                "I can help with:\n  - General conversation and questions\n  - System information\n  - File management\n  - Network diagnostics\n  - Code generation and review\n  - Web searches\n  - Data analysis\nJust tell me what you need!",
            ],
            "name": [
                "I'm the Web OS Chat Agent, part of the multi-agent AI system.",
                "You can call me Web OS Assistant! I'm powered by the agent system.",
            ],
            "capabilities": [
                "I can chat with you, answer questions, help with files, analyze data, check networks, generate code, search the web, and more! Try asking about any of these.",
            ],
            "default": [
                "That's interesting! I'm a simple chat agent in Web OS. For specialized tasks, I can route your request to the right agent.\n\nAvailable agents: File, Network, Device, Data, System, Scheduler, Code, Image, Search, Math, Translator",
            ],
        }

    def run(self, task):
        self.add_memory(f"Chat: {task}")
        t = task.lower().strip()

        if any(w in t for w in ["hi", "hello", "hey", "greetings", "sup", "howdy"]):
            return self._respond("greeting")
        if any(w in t for w in ["bye", "goodbye", "see you", "later", "exit", "quit"]):
            return self._respond("farewell")
        if any(w in t for w in ["thanks", "thank you", "appreciate", "thx"]):
            return self._respond("thanks")
        if any(w in t for w in ["help", "what can", "commands", "abilities"]):
            return self._respond("help")
        if any(w in t for w in ["your name", "who are you", "what are you"]):
            return self._respond("name")
        if any(w in t for w in ["capabilities", "what do you", "can you do"]):
            return self._respond("capabilities")
        if any(w in t for w in ["how are you", "how's it", "what's up"]):
            return f"I'm doing great, thanks for asking! I'm running on Web OS v6.0. How can I help you today?"
        if "time" in t:
            return f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if "joke" in t or "funny" in t:
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs!",
                "What do you call a fake noodle? An impasta!",
                "Why did the developer go broke? Because he used up all his cache!",
                "How many programmers does it take to change a light bulb? None, that's a hardware problem!",
            ]
            return random.choice(jokes)
        if "motivate" in t or "quote" in t:
            quotes = [
                "The best way to predict the future is to create it. - Peter Drucker",
                "Code is like humor. When you have to explain it, it's bad. - Cory House",
                "First, solve the problem. Then, write the code. - John Johnson",
                "Talk is cheap. Show me the code. - Linus Torvalds",
            ]
            return random.choice(quotes)
        return self._respond("default")

    def _respond(self, category):
        responses = self.responses.get(category, self.responses["default"])
        return f"ChatAgent: {random.choice(responses)}"
