# frontend/mips_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
from backend.mips_sim import MIPSSimulator  # Puxando o "cérebro" do projeto

class MIPS_GUI:
    def __init__(self, root):
        # Configuração básica da janela (tamanho, título)
        self.root = root
        self.root.title("MIPS Pipeline Simulator - Projeto Final")
        self.root.geometry("1100x700") # Tamanho HD pra caber tudo
        
        # Instancia o Backend (a lógica que a gente acabou de comentar)
        self.sim = MIPSSimulator()
        
        # Monta a tela
        self.create_widgets()

    def create_widgets(self):
        # --- PARTE DE CIMA: OS BOTÕES DE CONTROLE ---
        top = tk.Frame(self.root, pady=10)
        top.pack(fill="x") # Cola no topo e estica pros lados
        
        # Botão que pega o texto e joga na memória
        tk.Button(top, text="Carregar Código", command=self.load).pack(side="left", padx=10)
        
        # Botão de Pânico (Zera tudo)
        tk.Button(top, text="Reset", command=self.reset).pack(side="left")
        
        # O Botão Mágico: Avança 1 Ciclo de Clock
        tk.Button(top, text="Passo (Clock)", command=self.step, bg="#ddffdd").pack(side="left", padx=10)
        
        # Mostrador de Ciclos (pra gente saber se o Stall tá funcionando)
        self.lbl_cycle = tk.Label(top, text="Ciclo: 0", font=("Arial", 14, "bold"))
        self.lbl_cycle.pack(side="right", padx=20)

        # --- MEIOTA: CÓDIGO NA ESQUERDA, PIPELINE NA DIREITA ---
        # O PanedWindow permite arrastar a divisória no meio
        center = tk.PanedWindow(self.root, orient="horizontal")
        center.pack(fill="both", expand=True, padx=10)

        # >> Lado Esquerdo: O Editor de Texto
        frame_code = tk.LabelFrame(center, text="Assembly Code")
        center.add(frame_code, width=300)
        
        self.txt_code = tk.Text(frame_code, font=("Consolas", 11))
        self.txt_code.pack(fill="both", expand=True)
        
        # Já deixo um código pronto pro professor não ter trabalho de digitar
        self.txt_code.insert("1.0", """addi $t0, $zero, 10
addi $t1, $zero, 20
add $t2, $t0, $t1
sw $t2, 0($zero)
lw $t3, 0($zero)
add $t4, $t3, $t3""")

        # >> Lado Direito: A Visualização dos Estágios
        frame_pipe = tk.LabelFrame(center, text="Estágios do Pipeline")
        center.add(frame_pipe)
        
        self.pipe_labels = {}
        # Cores pastel pra cada estágio ficar bonito e fácil de ler
        colors = ["#ffcccc", "#ffe5cc", "#ffffcc", "#e5ffcc", "#ccffff"]
        stages = ["IF", "ID", "EX", "MEM", "WB"]
        
        for i, st in enumerate(stages):
            # Cria uma caixinha pra cada estágio
            f = tk.Frame(frame_pipe, bg=colors[i], pady=5, padx=5, relief="raised", bd=2)
            f.pack(fill="x", pady=5)
            
            # Nome do Estágio (IF, ID...)
            tk.Label(f, text=st, font=("Arial", 12, "bold"), bg=colors[i], width=5).pack(side="left")
            
            # O texto que vai mudar (ex: "add $t0...")
            l = tk.Label(f, text="", font=("Consolas", 11), bg=colors[i], anchor="w")
            l.pack(side="left", fill="x", expand=True)
            
            # Guardo a referência na lista pra poder atualizar depois
            self.pipe_labels[st] = l

        # --- PARTE DE BAIXO: OS REGISTRADORES ---
        bot = tk.LabelFrame(self.root, text="Banco de Registradores (Principais)")
        bot.pack(fill="x", padx=10, pady=10)
        
        self.reg_labels = []
        frame_regs = tk.Frame(bot)
        frame_regs.pack()
        
        # Só mostro os registradores que a gente usa, senão polui a tela
        show_regs = ["$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$s0", "$s1", "$s2", "$v0", "$a0"]
        for i, rname in enumerate(show_regs):
            l = tk.Label(frame_regs, text=f"{rname}: 0", width=12, relief="sunken", bg="white")
            l.grid(row=0, column=i, padx=2) # Grid organiza em tabela
            self.reg_labels.append((rname, l))

    # --- AÇÕES DOS BOTÕES ---

    def load(self):
        # 1. Pega todo o texto do editor
        code = self.txt_code.get("1.0", "end")
        # 2. Manda pro backend processar (parser)
        self.sim.load_program(code)
        # 3. Atualiza a tela pra mostrar tudo zerado
        self.update_view()
        messagebox.showinfo("Sucesso", "Código carregado na memória!")

    def reset(self):
        self.sim.reset()
        self.update_view()

    def step(self):
        # Manda o backend avançar 1 ciclo de clock
        self.sim.step()
        # Pega o estado novo e desenha na tela
        self.update_view()

    def update_view(self):
        """A função que faz a mágica visual acontecer"""
        
        # 1. Atualiza o contador de ciclos
        self.lbl_cycle.config(text=f"Ciclo: {self.sim.cycle_count}")
        
        # 2. Atualiza as caixinhas coloridas do Pipeline
        # Pega o texto pronto do backend (self.sim.pipeline_str)
        for st, txt in self.sim.pipeline_str.items():
            self.pipe_labels[st].config(text=txt)
            
        # 3. Atualiza os valores dos Registradores
        for rname, lbl in self.reg_labels:
            idx = self.sim.get_reg_idx(rname) # Descobre o índice (ex: $t0 -> 8)
            val = self.sim.regs[idx]          # Pega o valor real
            lbl.config(text=f"{rname}: {val}") # Atualiza o texto