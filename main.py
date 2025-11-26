# main.py
import tkinter as tk
from frontend.mips_gui import MIPS_GUI

if __name__ == "__main__":
    # Cria a janela principal
    root = tk.Tk()
    
    # Inicia a aplicação
    app = MIPS_GUI(root)
    
    # Mantém a janela aberta
    root.mainloop()