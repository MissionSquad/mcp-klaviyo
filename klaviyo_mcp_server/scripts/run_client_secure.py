import os
import json
import subprocess
import time
from getpass import getpass
from sys import platform

import psutil

API_KEY_CONFIG_PATH = ["mcpServers", "klaviyo", "env", "PRIVATE_API_KEY"]
IS_WINDOWS = platform == "win32"
IS_MAC = platform == "darwin"


class Client:
    def __init__(
        self,
        app_name,
        config_path_mac,
        config_path_windows,
        app_path_mac,
        app_path_windows,
    ):
        self.app_name = app_name
        self.config_path = config_path_windows if IS_WINDOWS else config_path_mac
        self.app_path = app_path_windows if IS_WINDOWS else app_path_mac

    def set_api_key_in_config(self, api_key):
        config = self.get_config()

        # Ensure the path exists
        d = config
        for key in API_KEY_CONFIG_PATH[:-1]:
            if key not in d or not isinstance(d[key], dict):
                d[key] = {}
            d = d[key]

        d[API_KEY_CONFIG_PATH[-1]] = api_key

        self.write_config(config)

    def remove_api_key_from_config(self):
        config = self.get_config()

        d = config
        for key in API_KEY_CONFIG_PATH[:-1]:
            d = d.get(key, {})

        if API_KEY_CONFIG_PATH[-1] in d:
            del d[API_KEY_CONFIG_PATH[-1]]

        self.write_config(config)

    def get_config(self):
        with open(self.config_path, "r") as f:
            return json.load(f)

    def write_config(self, config: dict):
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

    def is_running(self):
        for proc in psutil.process_iter(["name"]):
            try:
                if self.app_name == proc.info["name"]:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def quit(self):
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/F", "/IM", f"{self.app_name}.exe"])
        else:
            # Use AppleScript to quit app gracefully
            subprocess.run(
                ["osascript", "-e", f'tell application "{self.app_name}" to quit']
            )

    def launch(self):
        if IS_WINDOWS:
            subprocess.Popen([self.app_path])
        else:
            # Use 'open' to launch the app on macOS
            subprocess.Popen(["open", "-a", self.app_name])

    def run(self):
        if not (IS_WINDOWS or IS_MAC):
            print("This script only supports macOS and Windows.")
            exit(1)

        api_key = getpass("Enter your Klaviyo API key: ")

        self.set_api_key_in_config(api_key)
        print("API key set in config.")

        # If app is running, quit it and wait for it to exit
        if self.is_running():
            print(
                f"{self.app_name} is already running. Quitting it to reload config..."
            )
            self.quit()
            # Wait for it to fully exit
            while self.is_running():
                time.sleep(1)
            print(f"{self.app_name} has exited.")

        print(f"Launching {self.app_name}...")
        self.launch()
        # Wait for app to exit
        time.sleep(5)
        try:
            print(f"Waiting for {self.app_name} to exit...")
            while self.is_running():
                time.sleep(2)
        finally:
            print(f"{self.app_name} exited. Cleaning up config...")
            self.remove_api_key_from_config()
            print("API key removed from config.")


def run_claude():
    client = Client(
        app_name="Claude",
        config_path_mac=os.path.expanduser(
            "~/Library/Application Support/Claude/claude_desktop_config.json"
        ),
        app_path_mac="/Applications/Claude.app",
        config_path_windows=os.path.expanduser(
            r"~\AppData\Roaming\Claude\claude_desktop_config.json"
        ),
        app_path_windows=os.path.expanduser(
            r"~\AppData\Local\AnthropicClaude\claude.exe"
        ),
    )
    client.run()


def run_cursor():
    client = Client(
        app_name="Cursor",
        config_path_mac=os.path.expanduser("~/.cursor/mcp.json"),
        app_path_mac="/Applications/Cursor.app",
        config_path_windows=os.path.expanduser(r"~\.cursor\mcp.json"),
        app_path_windows=os.path.expanduser(
            r"~\AppData\Local\Programs\cursor\Cursor.exe"
        ),
    )
    client.run()
