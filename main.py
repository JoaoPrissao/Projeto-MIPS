# main.py
import tkinter as tk
from frontend.mips_gui import MIPS_GUI

if __name__ == "__main__":
    root = tk.Tk()
    app = MIPS_GUI(root)
    root.mainloop()