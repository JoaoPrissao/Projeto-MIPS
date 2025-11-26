class MIPSSimulator:
    def __init__(self):
        self.reset()

    def reset(self):
        self.regs = [0] * 32
        self.data_memory = {}
        self.inst_memory = []
        self.pc = 0
        self.cycle_count = 0
        
        # Registradores de Pipeline (Estados)
        # Guardamos strings descritivas para mostrar na interface
        self.pipeline_state = {
            "IF": "Vazio",
            "ID": "Vazio",
            "EX": "Vazio",
            "MEM": "Vazio",
            "WB": "Vazio"
        }
        
        # Latches internos (Dados reais)
        self.IF_ID = {"inst": None, "pc": 0}
        self.ID_EX = {"inst": None, "opcode": "", "rd": 0, "rs": 0, "rt": 0, "imm": 0, "rs_val": 0, "rt_val": 0}
        self.EX_MEM = {"inst": None, "alu_result": 0, "write_data": 0, "rd": 0, "opcode": ""}
        self.MEM_WB = {"inst": None, "read_data": 0, "alu_result": 0, "rd": 0, "opcode": ""}

        self.reg_map = {
            "$zero": 0, "$at": 1, "$v0": 2, "$v1": 3, "$a0": 4, "$a1": 5, "$a2": 6, "$a3": 7,
            "$t0": 8, "$t1": 9, "$t2": 10, "$t3": 11, "$t4": 12, "$t5": 13, "$t6": 14, "$t7": 15,
            "$s0": 16, "$s1": 17, "$s2": 18, "$s3": 19, "$s4": 20, "$s5": 21, "$s6": 22, "$s7": 23,
            "$t8": 24, "$t9": 25, "$k0": 26, "$k1": 27, "$gp": 28, "$sp": 29, "$fp": 30, "$ra": 31
        }
        self.reg_names = list(self.reg_map.keys())

    def load_program(self, text_instructions):
        self.reset()
        # Remove linhas vazias e espaços extras
        self.inst_memory = [line.strip() for line in text_instructions.split('\n') if line.strip()]

    def get_reg_idx(self, name):
        name = name.strip().replace(',', '')
        return self.reg_map.get(name, 0)


    def stage_WB(self):
        latch = self.MEM_WB
        if latch["inst"] is None:
            self.pipeline_state["WB"] = ""
            return

        desc = f"{latch['inst']}"
        if latch["opcode"] in ["add", "sub", "sll", "addi"] and latch["rd"] != 0:
            self.regs[latch["rd"]] = latch["alu_result"]
            desc += f" -> Reg${latch['rd']} = {latch['alu_result']}"
        elif latch["opcode"] == "lw" and latch["rd"] != 0:
            self.regs[latch["rd"]] = latch["read_data"]
            desc += f" -> Reg${latch['rd']} = {latch['read_data']}"
            
        self.pipeline_state["WB"] = desc

    def stage_MEM(self):
        latch = self.EX_MEM
        next_latch = self.MEM_WB
        
        if latch["inst"] is None:
            next_latch["inst"] = None
            self.pipeline_state["MEM"] = ""
            return

        desc = f"{latch['inst']}"
        
        # Copia dados
        for k in next_latch: next_latch[k] = latch.get(k, 0)
        next_latch["inst"] = latch["inst"]
        
        if latch["opcode"] == "lw":
            addr = latch["alu_result"]
            val = self.data_memory.get(addr, 0)
            next_latch["read_data"] = val
            desc += f" [Lendo Mem[{addr}] = {val}]"
        elif latch["opcode"] == "sw":
            addr = latch["alu_result"]
            val = latch["write_data"]
            self.data_memory[addr] = val
            desc += f" [Escrevendo Mem[{addr}] = {val}]"
            
        self.pipeline_state["MEM"] = desc

    def stage_EX(self):
        latch = self.ID_EX
        next_latch = self.EX_MEM
        
        if latch["inst"] is None:
            next_latch["inst"] = None
            self.pipeline_state["EX"] = ""
            return

        desc = f"{latch['inst']}"
        
        # Copia dados básicos
        next_latch["inst"] = latch["inst"]
        next_latch["opcode"] = latch["opcode"]
        next_latch["write_data"] = latch["rt_val"] 
        next_latch["rd"] = 0 # Default

        if latch["opcode"] == "add":
            res = latch["rs_val"] + latch["rt_val"]
            next_latch["alu_result"] = res
            next_latch["rd"] = latch["rd"]
            desc += f" [ULA: {latch['rs_val']} + {latch['rt_val']} = {res}]"
            
        elif latch["opcode"] == "sub":
            res = latch["rs_val"] - latch["rt_val"]
            next_latch["alu_result"] = res
            next_latch["rd"] = latch["rd"]
            desc += f" [ULA: {latch['rs_val']} - {latch['rt_val']} = {res}]"

        elif latch["opcode"] == "addi":
            res = latch["rs_val"] + latch["imm"]
            next_latch["alu_result"] = res
            next_latch["rd"] = latch["rt"]
            desc += f" [ULA: {latch['rs_val']} + {latch['imm']} = {res}]"
            
        elif latch["opcode"] == "sll":
            res = latch["rs_val"] << latch["imm"] # Usamos rs_val para simplificar parser, mas seria rt
            next_latch["alu_result"] = res
            next_latch["rd"] = latch["rd"]
            
        elif latch["opcode"] in ["lw", "sw"]:
            res = latch["rs_val"] + latch["imm"]
            next_latch["alu_result"] = res
            next_latch["rd"] = latch["rt"] # Para LW destino é rt
            desc += f" [Addr: {latch['rs_val']} + {latch['imm']} = {res}]"

        self.pipeline_state["EX"] = desc

    def stage_ID(self):
        latch = self.IF_ID
        next_latch = self.ID_EX
        
        if latch["inst"] is None:
            next_latch["inst"] = None
            self.pipeline_state["ID"] = ""
            return

        desc = f"{latch['inst']}"
        
        # Parser simples
        parts = latch["inst"].replace(',', '').split()
        opcode = parts[0]
        
        next_latch["inst"] = latch["inst"]
        next_latch["opcode"] = opcode
        
        try:
            if opcode in ["add", "sub"]:
                next_latch["rd"] = self.get_reg_idx(parts[1])
                next_latch["rs"] = self.get_reg_idx(parts[2])
                next_latch["rt"] = self.get_reg_idx(parts[3])
                next_latch["rs_val"] = self.regs[next_latch["rs"]]
                next_latch["rt_val"] = self.regs[next_latch["rt"]]
            
            elif opcode == "sll": # sll $rd, $rt, shamt
                 next_latch["rd"] = self.get_reg_idx(parts[1])
                 next_latch["rs_val"] = self.regs[self.get_reg_idx(parts[2])] # Pega valor
                 next_latch["imm"] = int(parts[3])

            elif opcode == "addi":
                next_latch["rt"] = self.get_reg_idx(parts[1])
                next_latch["rs"] = self.get_reg_idx(parts[2])
                next_latch["imm"] = int(parts[3])
                next_latch["rs_val"] = self.regs[next_latch["rs"]]

            elif opcode in ["lw", "sw"]: # lw $t0, 4($t1)
                if '(' in parts[2]:
                    offset, base = parts[2].replace(')', '').split('(')
                    next_latch["rt"] = self.get_reg_idx(parts[1])
                    next_latch["rs"] = self.get_reg_idx(base)
                    next_latch["imm"] = int(offset)
                else: # Suporte a formato simplificado lw $t0 $t1 4
                    next_latch["rt"] = self.get_reg_idx(parts[1])
                    next_latch["rs"] = self.get_reg_idx(parts[2])
                    next_latch["imm"] = int(parts[3])
                
                next_latch["rs_val"] = self.regs[next_latch["rs"]]
                next_latch["rt_val"] = self.regs[next_latch["rt"]] # Para SW
        except:
            desc += " (Erro Decode)"

        self.pipeline_state["ID"] = desc

    def stage_IF(self):
        next_latch = self.IF_ID
        
        if self.pc >= len(self.inst_memory) * 4:
            next_latch["inst"] = None
            self.pipeline_state["IF"] = ""
            return

        inst_idx = self.pc // 4
        instruction = self.inst_memory[inst_idx]
        
        next_latch["inst"] = instruction
        next_latch["pc"] = self.pc
        self.pc += 4
        
        self.pipeline_state["IF"] = f"{instruction} (PC={self.pc-4})"

    def step(self):
        """Executa UM ciclo de clock"""
        self.cycle_count += 1
        # Ordem inversa para simular paralelismo corretamente em software
        self.stage_WB()
        self.stage_MEM()
        self.stage_EX()
        self.stage_ID()
        self.stage_IF()
