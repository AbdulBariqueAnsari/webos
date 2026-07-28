import os, sys, json, importlib, inspect, threading, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

PLUGINS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "plugins")


class Plugin:
    name = "base"
    version = "1.0"
    description = "Base plugin"
    author = ""

    def on_load(self, app, hub):
        pass

    def on_unload(self):
        pass

    def get_routes(self):
        return []

    def get_agent(self):
        return None


class PluginLoader:
    def __init__(self, app=None, hub=None):
        self.plugins = {}
        self.app = app
        self.hub = hub
        self._watcher = None

    def discover(self):
        os.makedirs(PLUGINS_DIR, exist_ok=True)
        init = os.path.join(PLUGINS_DIR, "__init__.py")
        if not os.path.exists(init):
            with open(init, "w") as f:
                f.write("")

        for f in os.listdir(PLUGINS_DIR):
            if f.endswith(".py") and f != "__init__.py":
                self._load_plugin_file(os.path.join(PLUGINS_DIR, f))
            else:
                plugin_dir = os.path.join(PLUGINS_DIR, f)
                if os.path.isdir(plugin_dir) and not f.startswith("_") and f != "examples":
                    init_file = os.path.join(plugin_dir, "__init__.py")
                    if os.path.exists(init_file):
                        self._load_plugin_dir(plugin_dir)

    def _load_plugin_file(self, fpath):
        name = os.path.splitext(os.path.basename(fpath))[0]
        try:
            spec = importlib.util.spec_from_file_location(name, fpath)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for attr in dir(mod):
                    obj = getattr(mod, attr)
                    if isinstance(obj, type) and issubclass(obj, Plugin) and obj != Plugin:
                        plugin = obj()
                        plugin.on_load(self.app, self.hub)
                        self.plugins[plugin.name] = plugin
                        print(f"[Plugins] Loaded: {plugin.name} v{plugin.version}")
                        if plugin.get_agent():
                            self.hub.register(plugin.get_agent())
                        return plugin
        except Exception as e:
            print(f"[Plugins] Error loading {name}: {e}")
        return None

    def _load_plugin_dir(self, dirpath):
        name = os.path.basename(dirpath)
        try:
            spec = importlib.util.spec_from_file_location(name, os.path.join(dirpath, "__init__.py"))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for attr in dir(mod):
                    obj = getattr(mod, attr)
                    if isinstance(obj, type) and issubclass(obj, Plugin) and obj != Plugin:
                        plugin = obj()
                        plugin.on_load(self.app, self.hub)
                        self.plugins[plugin.name] = plugin
                        print(f"[Plugins] Loaded: {plugin.name} v{plugin.version}")
                        if plugin.get_agent():
                            self.hub.register(plugin.get_agent())
                        return plugin
        except Exception as e:
            print(f"[Plugins] Error loading {name}: {e}")
        return None

    def list_plugins(self):
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
            }
            for p in self.plugins.values()
        ]

    def get_plugin(self, name):
        return self.plugins.get(name)

    def unload(self, name):
        if name in self.plugins:
            try:
                self.plugins[name].on_unload()
            except Exception:
                pass
            del self.plugins[name]
            return True
        return False

    def reload_all(self):
        names = list(self.plugins.keys())
        for n in names:
            self.unload(n)
        self.discover()
