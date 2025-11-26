# backend/mips_sim.py
import copy

class MIPSSimulator:
    def __init__(self):
        self.reset()

    def reset(self):
        # Hardware básico: Registradores (0-31) e Memórias
        self.regs = [0] * 32
        self.data_memory = {}
        self.inst_memory = []
        self.pc = 0
        self.cycle_count = 0
        
        # Flag pra avisar o IF: "Ei, para tudo que deu ruim lá na frente!"
        self.stalled_flag = False 
        
        # Strings só pra mostrar na tela (boniteza pro usuário)
        self.pipeline_str = {"IF": "", "ID": "", "EX": "", "MEM": "", "WB": ""}
        
        # Latches (Os pacotes que viajam entre os estágios)
        self.IF_ID = {"inst": None, "pc": 0}
        
        # Começa tudo zerado pra não dar erro de "lixo de memória"
        self.ID_EX = self.empty_latch()
        self.EX_MEM = self.empty_latch()
        self.MEM_WB = self.empty_latch()

        # Mapa pra eu não ficar louco decorando número de registrador
        self.reg_map = {
            "$zero": 0, "$at": 1, "$v0": 2, "$v1": 3, "$a0": 4, "$a1": 5, "$a2": 6, "$a3": 7,
            "$t0": 8, "$t1": 9, "$t2": 10, "$t3": 11, "$t4": 12, "$t5": 13, "$t6": 14, "$t7": 15,
            "$s0": 16, "$s1": 17, "$s2": 18, "$s3": 19, "$s4": 20, "$s5": 21, "$s6": 22, "$s7": 23,
            "$t8": 24, "$t9": 25, "$k0": 26, "$k1": 27, "$gp": 28, "$sp": 29, "$fp": 30, "$ra": 31
        }

    def empty_latch(self):
        # Retorna um latch "limpo" (famosa Bolha ou NOP)
        return {"inst": None, "opcode": "", "rd": 0, "rs": 0, "rt": 0, "imm": 0, 
                "rs_val": 0, "rt_val": 0, "write_reg": 0, "alu_result": 0, 
                "write_data": 0, "read_data": 0}

    def load_program(self, text):
        self.reset()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        clean_insts = []
        self.labels = {}
        idx = 0
        # Passada rápida pra achar onde estão os Labels (ex: "loop:") e guardar o endereço
        for line in lines:
            if '#' in line: line = line.split('#')[0].strip()
            if not line: continue
            
            if line.endswith(':'):
                self.labels[line[:-1]] = idx * 4
            else:
                if ':' in line:
                    parts = line.split(':')
                    self.labels[parts[0].strip()] = idx * 4
                    clean_insts.append(parts[1].strip())
                else:
                    clean_insts.append(line)
                idx += 1
        self.inst_memory = clean_insts

    def get_reg_idx(self, name):
        return self.reg_map.get(name.strip().replace(',', ''), 0)

    # --- O MOTOR DO NEGÓCIO (CLOCK) ---
    def step(self):
        self.cycle_count += 1
        self.stalled_flag = False
        
        # [PULO DO GATO] O Snapshot:
        # No hardware real, tudo roda junto. No Python, é um por um.
        # Pra um estágio não atropelar o outro no mesmo ciclo, eu tiro uma "foto"
        # do estado atual. Todo mundo lê da FOTO e escreve no REAL.
        curr_IF_ID = copy.deepcopy(self.IF_ID)
        curr_ID_EX = copy.deepcopy(self.ID_EX)
        curr_EX_MEM = copy.deepcopy(self.EX_MEM)
        curr_MEM_WB = copy.deepcopy(self.MEM_WB)
        
        # Roda os estágios
        self.run_wb(curr_MEM_WB)
        self.run_mem(curr_EX_MEM)
        self.run_ex(curr_ID_EX, curr_EX_MEM, curr_MEM_WB) # EX precisa olhar pra frente (Forwarding)
        self.run_id(curr_IF_ID, curr_ID_EX) # ID precisa olhar pro EX (Hazard Detection)
        self.run_if() # IF obedece o ID (se tiver Stall)

    # --- WB (Finalizando) ---
    def run_wb(self, latch):
        if latch["inst"] is None:
            self.pipeline_str["WB"] = ""
            return

        # O dado veio da Memória (LW) ou da conta (ADD)?
        result = latch["read_data"] if latch["opcode"] == "lw" else latch["alu_result"]

        # Grava de verdade no banco (menos no $zero, que é sagrado)
        if latch["write_reg"] != 0:
            self.regs[latch["write_reg"]] = result
            
        self.pipeline_str["WB"] = f"{latch['inst']} -> ${latch['write_reg']}={result}"

    # --- MEM (Acessando RAM) ---
    def run_mem(self, latch):
        # Limpa o próximo estágio antes de mandar coisa nova
        self.MEM_WB.update(self.empty_latch())
        next_latch = self.MEM_WB
        
        if latch["inst"] is None:
            next_latch["inst"] = None
            self.pipeline_str["MEM"] = ""
            return

        next_latch.update(latch) # Passa tudo adiante
        
        desc = f"{latch['inst']}"
        
        # Só LW e SW mexem aqui
        if latch["opcode"] == "lw":
            addr = latch["alu_result"]
            val = self.data_memory.get(addr, 0)
            next_latch["read_data"] = val
            desc += f" [Lê Mem[{addr}]={val}]"
            
        elif latch["opcode"] == "sw":
            addr = latch["alu_result"]
            val = latch["write_data"]
            self.data_memory[addr] = val
            desc += f" [Grava Mem[{addr}]={val}]"
            
        self.pipeline_str["MEM"] = desc

    # --- EX (Onde a mágica acontece) ---
    def run_ex(self, latch, hazard_ex_mem, hazard_mem_wb):
        self.EX_MEM.update(self.empty_latch())
        next_latch = self.EX_MEM
        
        if latch["inst"] is None:
            next_latch["inst"] = None
            self.pipeline_str["EX"] = ""
            return

        # Pega os valores originais que vieram lá do ID
        op1 = latch["rs_val"]
        op2 = latch["rt_val"]
        
        # --- FORWARDING UNIT (O "Gato" de dados) ---
        # Se o dado que eu preciso tá logo ali na frente (EX/MEM), eu pego agora!
        # Isso evita esperar gravar no banco.
        
        # Checa RS
        if hazard_ex_mem["write_reg"] != 0 and hazard_ex_mem["write_reg"] == latch["rs"]:
            op1 = hazard_ex_mem["alu_result"] # Peguei do vizinho!
        elif hazard_mem_wb["write_reg"] != 0 and hazard_mem_wb["write_reg"] == latch["rs"]:
            # Peguei do vizinho de 2 casas (MEM/WB), mas só se o de 1 casa não tiver sobrescrito
            if hazard_mem_wb["opcode"] == "lw":
                op1 = hazard_mem_wb["read_data"]
            else:
                op1 = hazard_mem_wb["alu_result"]

        # Checa RT (Mesma lógica)
        if hazard_ex_mem["write_reg"] != 0 and hazard_ex_mem["write_reg"] == latch["rt"]:
            op2 = hazard_ex_mem["alu_result"]
        elif hazard_mem_wb["write_reg"] != 0 and hazard_mem_wb["write_reg"] == latch["rt"]:
            if hazard_mem_wb["opcode"] == "lw":
                op2 = hazard_mem_wb["read_data"]
            else:
                op2 = hazard_mem_wb["alu_result"]

        # --- ULA (Calculadora) ---
        res = 0
        opcode = latch["opcode"]
        
        if opcode == "add": res = op1 + op2
        elif opcode == "sub": res = op1 - op2
        elif opcode == "addi": res = op1 + latch["imm"]
        elif opcode == "sll": res = op1 << latch["imm"]
        elif opcode in ["lw", "sw"]: res = op1 + latch["imm"] # Calcula endereço

        next_latch.update(latch)
        next_latch["alu_result"] = res
        next_latch["write_data"] = op2 # O valor pro SW já vai corrigido pelo Forwarding
        
        self.pipeline_str["EX"] = f"{latch['inst']} [Res={res}]"

    # --- ID (Decodifica e vigia perigos) ---
    def run_id(self, latch, hazard_id_ex):
        self.ID_EX.update(self.empty_latch())
        next_latch = self.ID_EX
        
        if latch["inst"] is None:
            self.pipeline_str["ID"] = ""
            return

        # Quebra a string da instrução (Parser simplão)
        parts = latch["inst"].replace(',', '').split()
        opcode = parts[0]
        rs, rt, rd, imm, write_reg = 0, 0, 0, 0, 0

        try:
            # Descobre quem é quem na instrução
            if opcode in ["add", "sub"]:
                rd, rs, rt = [self.get_reg_idx(p) for p in parts[1:4]]
                write_reg = rd
            elif opcode == "addi":
                rt = self.get_reg_idx(parts[1])
                rs = self.get_reg_idx(parts[2])
                imm = int(parts[3])
                write_reg = rt
            elif opcode == "sll":
                rd = self.get_reg_idx(parts[1])
                rs = self.get_reg_idx(parts[2])
                imm = int(parts[3])
                write_reg = rd
            elif opcode in ["lw", "sw"]:
                rt = self.get_reg_idx(parts[1])
                if '(' in parts[2]: # Formato offset(base)
                    off_s, base_s = parts[2].replace(')', '').split('(')
                    imm = int(off_s)
                    rs = self.get_reg_idx(base_s)
                else:
                    rs = self.get_reg_idx(parts[2])
                    imm = int(parts[3])
                write_reg = rt if opcode == "lw" else 0
            elif opcode == "beq":
                rs, rt = [self.get_reg_idx(p) for p in parts[1:3]]
                dest = parts[3]
                imm = self.labels.get(dest, int(dest) if dest.isdigit() or dest.startswith('-') else 0)
            elif opcode == "j":
                dest = parts[1]
                imm = self.labels.get(dest, int(dest) if dest.isdigit() else 0)
        except: pass

        # --- DETECTOR DE PERIGO (Load-Use Hazard) ---
        # Se a instrução que tá indo pro EX é um LW e eu preciso do dado dela...
        is_load_use = False
        if hazard_id_ex["opcode"] == "lw":
            target = hazard_id_ex["write_reg"]
            if target != 0:
                if target == rs and opcode != "j": is_load_use = True
                if target == rt and opcode in ["add", "sub", "beq", "sw"]: is_load_use = True
        
        if is_load_use:
            # TRAVA TUDO! (Stall)
            self.stalled_flag = True # Avisa o IF pra não andar
            next_latch.update(self.empty_latch()) # Manda uma BOLHA pro EX
            self.pipeline_str["ID"] = f"{latch['inst']} (STALL - Load-Use)"
            return # Sai daqui e tenta de novo no próximo ciclo

        # --- CONTROLE DE DESVIO (Branch) ---
        rs_val = self.regs[rs]
        rt_val = self.regs[rt]
        
        if opcode == "beq":
            if rs_val == rt_val: # Se for igual, pula!
                # Calcula endereço novo
                self.pc = (latch["pc"] + 4 + (imm * 4)) if isinstance(imm, int) and imm < 1000 else imm
                
                # FLUSH: Limpa a instrução errada que entrou no IF
                self.IF_ID["inst"] = None 
                # BOLHA: O Branch morre aqui, não vai pro EX
                next_latch.update(self.empty_latch()) 
                
                self.pipeline_str["ID"] = f"BEQ Tomado -> Pula pra {self.pc}"
                return
        elif opcode == "j":
            self.pc = imm
            self.IF_ID["inst"] = None # Flush
            next_latch.update(self.empty_latch())
            self.pipeline_str["ID"] = f"JUMP -> Pula pra {self.pc}"
            return

        # Se tá tudo em paz, passa os dados pro próximo estágio
        next_latch.update({
            "inst": latch["inst"], "opcode": opcode,
            "rs": rs, "rt": rt, "rd": rd, "imm": imm,
            "rs_val": rs_val, "rt_val": rt_val, "write_reg": write_reg
        })
        
        self.pipeline_str["ID"] = f"{latch['inst']}"

    # --- IF (Busca) ---
    def run_if(self):
        # O ID mandou parar? Então não busca nada novo.
        if self.stalled_flag:
            self.pipeline_str["IF"] = f"{self.IF_ID['inst']} (Stall)"
            return

        if self.pc >= len(self.inst_memory) * 4:
            self.IF_ID["inst"] = None
            self.pipeline_str["IF"] = ""
            return

        # Pega a instrução e incrementa o PC
        idx = self.pc // 4
        if idx < len(self.inst_memory):
            inst = self.inst_memory[idx]
            self.IF_ID["inst"] = inst
            self.IF_ID["pc"] = self.pc
            self.pc += 4
            self.pipeline_str["IF"] = inst
        else:
            self.IF_ID["inst"] = None