# backend/mips_sim.py
import copy

class MIPSSimulator:
    def __init__(self):
        self.reset()

    def reset(self):
        self.regs = [0] * 32
        self.data_memory = {}
        self.inst_memory = []
        self.pc = 0
        self.cycle_count = 0
        self.stalled_flag = False 
        
        self.pipeline_str = {"IF": "", "ID": "", "EX": "", "MEM": "", "WB": ""}
        
        # Latches (Registradores de Pipeline)
        self.IF_ID = {"inst": None, "pc": 0}
        # Inicializa com todos os campos zerados para evitar lixo de memória
        self.ID_EX = self.empty_latch()
        self.EX_MEM = self.empty_latch()
        self.MEM_WB = self.empty_latch()

        self.reg_map = {
            "$zero": 0, "$at": 1, "$v0": 2, "$v1": 3, "$a0": 4, "$a1": 5, "$a2": 6, "$a3": 7,
            "$t0": 8, "$t1": 9, "$t2": 10, "$t3": 11, "$t4": 12, "$t5": 13, "$t6": 14, "$t7": 15,
            "$s0": 16, "$s1": 17, "$s2": 18, "$s3": 19, "$s4": 20, "$s5": 21, "$s6": 22, "$s7": 23,
            "$t8": 24, "$t9": 25, "$k0": 26, "$k1": 27, "$gp": 28, "$sp": 29, "$fp": 30, "$ra": 31
        }

    def empty_latch(self):
        """Cria um estado vazio para limpar registradores de pipeline"""
        return {"inst": None, "opcode": "", "rd": 0, "rs": 0, "rt": 0, "imm": 0, 
                "rs_val": 0, "rt_val": 0, "write_reg": 0, "alu_result": 0, 
                "write_data": 0, "read_data": 0}

    def load_program(self, text):
        self.reset()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        clean_insts = []
        self.labels = {}
        idx = 0
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

    # --- STEP ---
    def step(self):
        self.cycle_count += 1
        self.stalled_flag = False
        
        # SNAPSHOT
        curr_IF_ID = copy.deepcopy(self.IF_ID)
        curr_ID_EX = copy.deepcopy(self.ID_EX)
        curr_EX_MEM = copy.deepcopy(self.EX_MEM)
        curr_MEM_WB = copy.deepcopy(self.MEM_WB)
        
        # EXECUÇÃO
        self.run_wb(curr_MEM_WB)
        self.run_mem(curr_EX_MEM)
        self.run_ex(curr_ID_EX, curr_EX_MEM, curr_MEM_WB)
        self.run_id(curr_IF_ID, curr_ID_EX)
        self.run_if()

    # --- WB ---
    def run_wb(self, latch):
        if latch["inst"] is None:
            self.pipeline_str["WB"] = ""
            return

        result = 0
        if latch["opcode"] == "lw":
            result = latch["read_data"]
        else:
            result = latch["alu_result"]

        if latch["write_reg"] != 0:
            self.regs[latch["write_reg"]] = result
            
        self.pipeline_str["WB"] = f"{latch['inst']} -> ${latch['write_reg']}={result}"

    # --- MEM ---
    def run_mem(self, latch):
        # Limpa o próximo latch antes de escrever
        self.MEM_WB.update(self.empty_latch())
        next_latch = self.MEM_WB
        
        if latch["inst"] is None:
            next_latch["inst"] = None
            self.pipeline_str["MEM"] = ""
            return

        next_latch.update(latch) # Copia tudo
        
        desc = f"{latch['inst']}"
        
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

    # --- EX ---
    def run_ex(self, latch, hazard_ex_mem, hazard_mem_wb):
        # Limpa o próximo latch
        self.EX_MEM.update(self.empty_latch())
        next_latch = self.EX_MEM
        
        if latch["inst"] is None:
            next_latch["inst"] = None
            self.pipeline_str["EX"] = ""
            return

        op1 = latch["rs_val"]
        op2 = latch["rt_val"]
        
        # FORWARDING UNIT
        # 1. Forward do Vizinho (EX/MEM)
        if hazard_ex_mem["write_reg"] != 0 and hazard_ex_mem["write_reg"] == latch["rs"]:
            op1 = hazard_ex_mem["alu_result"]
        elif hazard_mem_wb["write_reg"] != 0 and hazard_mem_wb["write_reg"] == latch["rs"]:
            # 2. Forward do Vizinho Distante (MEM/WB)
            if hazard_mem_wb["opcode"] == "lw":
                op1 = hazard_mem_wb["read_data"]
            else:
                op1 = hazard_mem_wb["alu_result"]

        if hazard_ex_mem["write_reg"] != 0 and hazard_ex_mem["write_reg"] == latch["rt"]:
            op2 = hazard_ex_mem["alu_result"]
        elif hazard_mem_wb["write_reg"] != 0 and hazard_mem_wb["write_reg"] == latch["rt"]:
            if hazard_mem_wb["opcode"] == "lw":
                op2 = hazard_mem_wb["read_data"]
            else:
                op2 = hazard_mem_wb["alu_result"]

        res = 0
        opcode = latch["opcode"]
        
        if opcode == "add": res = op1 + op2
        elif opcode == "sub": res = op1 - op2
        elif opcode == "addi": res = op1 + latch["imm"]
        elif opcode == "sll": res = op1 << latch["imm"]
        elif opcode in ["lw", "sw"]: res = op1 + latch["imm"]

        next_latch.update(latch)
        next_latch["alu_result"] = res
        next_latch["write_data"] = op2
        
        self.pipeline_str["EX"] = f"{latch['inst']} [Res={res}]"

    # --- ID ---
    def run_id(self, latch, hazard_id_ex):
        # Limpa o próximo latch (MUITO IMPORTANTE PARA EVITAR O BUG DO STALL)
        self.ID_EX.update(self.empty_latch())
        next_latch = self.ID_EX
        
        if latch["inst"] is None:
            self.pipeline_str["ID"] = ""
            return

        parts = latch["inst"].replace(',', '').split()
        opcode = parts[0]
        rs, rt, rd, imm, write_reg = 0, 0, 0, 0, 0

        try:
            if opcode in ["add", "sub"]:
                rd = self.get_reg_idx(parts[1])
                rs = self.get_reg_idx(parts[2])
                rt = self.get_reg_idx(parts[3])
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
                if '(' in parts[2]:
                    off_s, base_s = parts[2].replace(')', '').split('(')
                    imm = int(off_s)
                    rs = self.get_reg_idx(base_s)
                else:
                    rs = self.get_reg_idx(parts[2])
                    imm = int(parts[3])
                write_reg = rt if opcode == "lw" else 0
            elif opcode == "beq":
                rs = self.get_reg_idx(parts[1])
                rt = self.get_reg_idx(parts[2])
                dest = parts[3]
                imm = self.labels.get(dest, int(dest) if dest.isdigit() or dest.startswith('-') else 0)
            elif opcode == "j":
                dest = parts[1]
                imm = self.labels.get(dest, int(dest) if dest.isdigit() else 0)
        except: pass

        # HAZARD DETECTION (LOAD-USE)
        is_load_use = False
        if hazard_id_ex["opcode"] == "lw":
            target = hazard_id_ex["write_reg"]
            if target != 0:
                if target == rs and opcode != "j": is_load_use = True
                if target == rt and opcode in ["add", "sub", "beq", "sw"]: is_load_use = True
        
        if is_load_use:
            self.stalled_flag = True
            # AQUI ESTAVA O ERRO: Garantimos que o próximo estágio receba uma bolha LIMPA
            next_latch.update(self.empty_latch()) 
            next_latch["inst"] = None
            self.pipeline_str["ID"] = f"{latch['inst']} (STALL Load-Use)"
            return

        # BRANCH CONTROL
        rs_val = self.regs[rs]
        rt_val = self.regs[rt]
        
        if opcode == "beq":
            if rs_val == rt_val:
                if isinstance(imm, int) and imm < 1000: self.pc = latch["pc"] + 4 + (imm * 4)
                else: self.pc = imm
                self.IF_ID["inst"] = None # Flush IF
                next_latch.update(self.empty_latch()) # Bolha EX
                self.pipeline_str["ID"] = f"BEQ Tomado -> {self.pc}"
                return
        elif opcode == "j":
            self.pc = imm
            self.IF_ID["inst"] = None
            next_latch.update(self.empty_latch())
            self.pipeline_str["ID"] = f"JUMP -> {self.pc}"
            return

        # Passa dados (Sem Stall)
        next_latch["inst"] = latch["inst"]
        next_latch["opcode"] = opcode
        next_latch["rs"] = rs
        next_latch["rt"] = rt
        next_latch["rd"] = rd
        next_latch["imm"] = imm
        next_latch["rs_val"] = rs_val
        next_latch["rt_val"] = rt_val
        next_latch["write_reg"] = write_reg
        
        self.pipeline_str["ID"] = f"{latch['inst']}"

    # --- IF ---
    def run_if(self):
        if self.stalled_flag:
            self.pipeline_str["IF"] = f"{self.IF_ID['inst']} (Stall)"
            return

        if self.pc >= len(self.inst_memory) * 4:
            self.IF_ID["inst"] = None
            self.pipeline_str["IF"] = ""
            return

        idx = self.pc // 4
        if idx < len(self.inst_memory):
            inst = self.inst_memory[idx]
            self.IF_ID["inst"] = inst
            self.IF_ID["pc"] = self.pc
            self.pc += 4
            self.pipeline_str["IF"] = inst
        else:
            self.IF_ID["inst"] = None