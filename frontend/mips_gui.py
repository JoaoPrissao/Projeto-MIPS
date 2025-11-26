# frontend/mips_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
from backend.mips_sim import MIPSSimulator  # Importa a lógica

class MIPS_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MIPS Pipeline Simulator")
        self.root.geometry("1100x700")
        
        # Instancia o Backend
        self.sim = MIPSSimulator()
        
        self.create_widgets()

    def create_widgets(self):
        # Topo
        top = tk.Frame(self.root, pady=10)
        top.pack(fill="x")
        
        tk.Button(top, text="Carregar Código", command=self.load).pack(side="left", padx=10)
        tk.Button(top, text="Reset", command=self.reset).pack(side="left")
        tk.Button(top, text="Passo (Clock)", command=self.step, bg="#ddffdd").pack(side="left", padx=10)
        self.lbl_cycle = tk.Label(top, text="Ciclo: 0", font=("Arial", 14, "bold"))
        self.lbl_cycle.pack(side="right", padx=20)

        # Centro
        center = tk.PanedWindow(self.root, orient="horizontal")
        center.pack(fill="both", expand=True, padx=10)

        # Editor
        frame_code = tk.LabelFrame(center, text="Assembly Code")
        center.add(frame_code, width=300)
        self.txt_code = tk.Text(frame_code, font=("Consolas", 11))
        self.txt_code.pack(fill="both", expand=True)
        
        # Código padrão para teste
        self.txt_code.insert("1.0", """addi $t0, $zero, 10
addi $t1, $zero, 20
add $t2, $t0, $t1
sw $t2, 0($zero)
lw $t3, 0($zero)
add $t4, $t3, $t3""")

        # Pipeline Visual
        frame_pipe = tk.LabelFrame(center, text="Pipeline Stages")
        center.add(frame_pipe)
        
        self.pipe_labels = {}
        colors = ["#ffcccc", "#ffe5cc", "#ffffcc", "#e5ffcc", "#ccffff"]
        stages = ["IF", "ID", "EX", "MEM", "WB"]
        
        for i, st in enumerate(stages):
            f = tk.Frame(frame_pipe, bg=colors[i], pady=5, padx=5, relief="raised", bd=2)
            f.pack(fill="x", pady=5)
            tk.Label(f, text=st, font=("Arial", 12, "bold"), bg=colors[i], width=5).pack(side="left")
            l = tk.Label(f, text="", font=("Consolas", 11), bg=colors[i], anchor="w")
            l.pack(side="left", fill="x", expand=True)
            self.pipe_labels[st] = l

        # Baixo: Registradores
        bot = tk.LabelFrame(self.root, text="Registradores Principais")
        bot.pack(fill="x", padx=10, pady=10)
        
        self.reg_labels = []
        frame_regs = tk.Frame(bot)
        frame_regs.pack()
        
        show_regs = ["$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$s0", "$s1", "$s2", "$v0", "$a0"]
        for i, rname in enumerate(show_regs):
            l = tk.Label(frame_regs, text=f"{rname}: 0", width=12, relief="sunken", bg="white")
            l.grid(row=0, column=i, padx=2)
            self.reg_labels.append((rname, l))

    def load(self):
        code = self.txt_code.get("1.0", "end")
        self.sim.load_program(code)
        self.update_view()
        messagebox.showinfo("OK", "Código carregado!")

    def reset(self):
        self.sim.reset()
        self.update_view()

    def step(self):
        self.sim.step()
        self.update_view()

    def update_view(self):
        self.lbl_cycle.config(text=f"Ciclo: {self.sim.cycle_count}")
        
        for st, txt in self.sim.pipeline_str.items():
            self.pipe_labels[st].config(text=txt)
            
        for rname, lbl in self.reg_labels:
            idx = self.sim.get_reg_idx(rname)
            val = self.sim.regs[idx]
            lbl.config(text=f"{rname}: {val}")