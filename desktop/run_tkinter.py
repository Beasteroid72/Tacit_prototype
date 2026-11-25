import os
import shutil
import subprocess
import tkinter as tk

from app_tkinter import TacitApp

OLLAMA_TIMEOUT = 1.0


def ensure_ollama_server():
    """Start the Ollama server if it isn't running yet (so llama is ready)."""
    try:
        import requests
    except ImportError:
        return
    try:
        r = requests.get("http://localhost:11434/api/version",
                         timeout=OLLAMA_TIMEOUT)
        if r.ok:
            return
    except Exception:
        pass
    ollama = shutil.which("ollama")
    if ollama is None:
        candidate = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        if os.path.exists(candidate):
            ollama = candidate
    if ollama is None:
        return
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen([ollama, "serve"], creationflags=flags)
    except Exception:
        pass


def main():
    ensure_ollama_server()
    root = tk.Tk()
    app = TacitApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()



