"""Entry point for the original Tkinter interface: python run_tkinter.py"""

import tkinter as tk

from app_tkinter import TacitApp
from engine import ensure_ollama_server


def main():
    ensure_ollama_server()
    root = tk.Tk()
    TacitApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
