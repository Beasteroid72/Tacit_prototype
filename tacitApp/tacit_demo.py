import tkinter as tk
from tacit_app import TacitApp


def main():
    root = tk.Tk()
    app = TacitApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
