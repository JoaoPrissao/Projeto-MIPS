# frontend/mips_gui.py
import tkinter as tk
from tkinter import ttk, messagebox

# Importando a lógica da outra pasta
from backend.mips_sim import MIPSSimulator

class MIPS_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador MIPS Pipeline")
        
        # Instancia o simulador que importamos
        self.sim = MIPSSimulator()

        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Pipeline.TLabel", font=("Arial", 10, "bold"), background="#e1e1e1", padding=5)
        style.configure("Stage.TFrame", relief="solid", borderwidth=1)

    def create_widgets(self):
        # 1. Painel de Controle (Topo)
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill="x")

        ttk.Label(control_frame, text="Código Assembly:").pack(side="left")
        
        self.btn_load = ttk.Button(control_frame, text="Carregar & Resetar", command=self.load_program)
        self.btn_load.pack(side="left", padx=5)
        
        self.btn_step = ttk.Button(control_frame, text="Próximo Ciclo (Step)", command=self.step_cycle)
        self.btn_step.pack(side="left", padx=5)

        self.lbl_cycle = ttk.Label(control_frame, text="Ciclo: 0", font=("Arial", 12, "bold"))
        self.lbl_cycle.pack(side="right", padx=10)

        #2. Área Principal (Dividida em Esquerda e Direita)
        main_pane = ttk.PanedWindow(self.root, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=5)

        # ESQUERDA: Editor de Código
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Editor de Código").pack(anchor="w")
        self.code_editor = tk.Text(left_frame, height=20, width=30, font=("Consolas", 11))
        self.code_editor.pack(fill="both", expand=True)
        
        # Código de exemplo padrão
        default_code = """addi $t0, $zero, 10
addi $t1, $zero, 5
add $t2, $t0, $t1
sw $t2, 0($zero)
lw $t3, 0($zero)"""
        self.code_editor.insert("1.0", default_code)

        # DIREITA: Visualização do Pipeline
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=3)

        ttk.Label(right_frame, text="Estágios do Pipeline").pack(anchor="w", pady=5)
        
        self.pipeline_labels = {}
        colors = ["#FFCCCC", "#FFE5CC", "#FFFFCC", "#E5FFCC", "#CCFFFF"] # Cores para IF, ID, EX, MEM, WB
        stages = ["IF", "ID", "EX", "MEM", "WB"]
        
        for i, stage in enumerate(stages):
            frame = tk.Frame(right_frame, bg=colors[i], bd=1, relief="solid")
            frame.pack(fill="x", pady=2, padx=5)
            
            lbl_title = tk.Label(frame, text=f"{stage}", bg=colors[i], font=("Arial", 10, "bold"), width=5)
            lbl_title.pack(side="left")
            
            lbl_info = tk.Label(frame, text="[Vazio]", bg=colors[i], font=("Consolas", 10), anchor="w")
            lbl_info.pack(side="left", fill="x", expand=True)
            
            self.pipeline_labels[stage] = lbl_info

        # 3. Área Inferior (Registradores e Memória)
        bottom_frame = ttk.LabelFrame(self.root, text="Estado do Processador", padding="10")
        bottom_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Registradores (Grid)
        reg_frame = ttk.Frame(bottom_frame)
        reg_frame.pack(side="left", fill="both", expand=True)
        
        self.reg_labels = []
        for i in range(32):
            lbl = tk.Label(reg_frame, text=f"${i}: 0", font=("Consolas", 9), width=10, anchor="w", bg="white", relief="sunken")
            lbl.grid(row=i%8, column=i//8, padx=2, pady=2)
            self.reg_labels.append(lbl)

        # Memória de Dados
        mem_frame = ttk.Frame(bottom_frame)
        mem_frame.pack(side="right", fill="y", padx=10)
        ttk.Label(mem_frame, text="Memória de Dados (Não-Zero)").pack()
        
        self.mem_list = tk.Listbox(mem_frame, width=25, font=("Consolas", 9))
        self.mem_list.pack(fill="y", expand=True)

    def load_program(self):
        code = self.code_editor.get("1.0", "end")
        self.sim.load_program(code)
        self.update_gui()
        messagebox.showinfo("Info", "Programa carregado! Registradores e Pipeline resetados.")

    def step_cycle(self):
        self.sim.step()
        self.update_gui()

    def update_gui(self):
        # Atualiza contador de ciclos
        self.lbl_cycle.config(text=f"Ciclo: {self.sim.cycle_count}")

        # Atualiza Pipeline
        for stage, info in self.sim.pipeline_state.items():
            text = info if info else "[Bolha / Vazio]"
            self.pipeline_labels[stage].config(text=text)

        # Atualiza Registradores
        for i, val in enumerate(self.sim.regs):
            # Mostra nome amigável ($t0, $zero) e valor
            name = self.sim.reg_names[i]
            self.reg_labels[i].config(text=f"{name}: {val}")
            # Destaca se valor mudou (opcional, teria que guardar estado anterior)

        # Atualiza Memória
        self.mem_list.delete(0, "end")
        for addr, val in self.sim.data_memory.items():
            self.mem_list.insert("end", f"Addr {addr}: {val}")

# Inicialização
if __name__ == "__main__":
    root = tk.Tk()
    app = MIPS_GUI(root)
    root.mainloop()