import random

class CacheLine:
    def __init__(self, block_size):
        self.valid = False
        self.tag = 0
        self.dirty = False
        self.data = [0] * block_size
        self.last_access = 0

class Cache:
    def __init__(self, memory_ref, num_lines=8, block_size=4):
        self.memory_ref = memory_ref
        self.num_lines = num_lines
        self.block_size = block_size
        self.lines = [CacheLine(block_size) for _ in range(num_lines)]
        self.hits = 0
        self.misses = 0
        self.log = []

    def _get_line_index(self, address):
        return (address // self.block_size) % self.num_lines

    def _get_tag(self, address):
        return address // (self.block_size * self.num_lines)

    def _get_block_start_address(self, address):
        return (address // self.block_size) * self.block_size

    def read(self, address):
        line_idx = self._get_line_index(address)
        tag = self._get_tag(address)
        offset = address % self.block_size
        line = self.lines[line_idx]

        if line.valid and line.tag == tag:
            self.hits += 1
            self.log.append(f"Cache HIT em {address} (L{line_idx})")
            return line.data[offset]
        else:
            self.misses += 1
            self.log.append(f"Cache MISS em {address}. Buscando RAM...")
            # Write-Back: Se a linha atual está suja, salva na RAM antes de substituir
            if line.valid and line.dirty:
                self._write_back_line(line_idx)
            
            # Carregar novo bloco
            block_start = self._get_block_start_address(address)
            for i in range(self.block_size):
                if block_start + i < len(self.memory_ref):
                    line.data[i] = self.memory_ref[block_start + i]
            
            line.valid = True
            line.tag = tag
            line.dirty = False
            return line.data[offset]

    def write(self, address, value):
        line_idx = self._get_line_index(address)
        tag = self._get_tag(address)
        offset = address % self.block_size
        line = self.lines[line_idx]

        # Política Write-Allocate: Se não está na cache, traz primeiro
        if not (line.valid and line.tag == tag):
            self.misses += 1
            self.log.append(f"Cache WRITE MISS em {address}. Alocando...")
            if line.valid and line.dirty:
                self._write_back_line(line_idx)
            
            block_start = self._get_block_start_address(address)
            for i in range(self.block_size):
                if block_start + i < len(self.memory_ref):
                    line.data[i] = self.memory_ref[block_start + i]
            line.valid = True
            line.tag = tag
        else:
            self.hits += 1
            self.log.append(f"Cache WRITE HIT em {address}")

        # Atualiza apenas na cache e marca como sujo
        line.data[offset] = value
        line.dirty = True

    def _write_back_line(self, line_idx):
        """Função auxiliar para escrever uma linha específica na RAM"""
        line = self.lines[line_idx]
        old_block_addr = (line.tag * self.num_lines * self.block_size) + (line_idx * self.block_size)
        self.log.append(f"Write-Back: Salvando Bloco {old_block_addr} na RAM")
        for i in range(self.block_size):
            if old_block_addr + i < len(self.memory_ref):
                self.memory_ref[old_block_addr + i] = line.data[i]
        line.dirty = False

    def flush_all(self):
        """Força a escrita de todas as linhas sujas na RAM (Usado no HALT)"""
        flushed_count = 0
        for i in range(self.num_lines):
            if self.lines[i].valid and self.lines[i].dirty:
                self._write_back_line(i)
                flushed_count += 1
        if flushed_count > 0:
            self.log.append(f"FLUSH: {flushed_count} blocos sincronizados com a RAM.")

class MIC1Hardware:
    def __init__(self):
        self.MEMORY_SIZE = 4096
        self.memory = [0] * self.MEMORY_SIZE
        self.cache = Cache(self.memory, num_lines=8, block_size=4) 

        self.registers = {
            'PC': 0, 'AC': 0, 'SP': 4095, 
            'IR': 0, 'TIR': 0, 'MAR': 0, 'MBR': 0,
            'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0 
        }
        self.halted = False
        self.micro_log = [] 

    def reset(self):
        self.memory = [0] * self.MEMORY_SIZE
        self.cache = Cache(self.memory, num_lines=8, block_size=4)
        self.registers = {k: 0 for k in self.registers}
        self.registers['SP'] = 4095
        self.halted = False
        self.micro_log = []

    def load_program(self, program_data):
        self.reset()
        for i, value in enumerate(program_data):
            if i < self.MEMORY_SIZE:
                self.memory[i] = value
                
    def _read_mem(self, addr):
        if 0 <= addr < self.MEMORY_SIZE:
            self.registers['MAR'] = addr
            val = self.cache.read(addr)
            self.registers['MBR'] = val
            return val
        return 0

    def _write_mem(self, addr, val):
        if 0 <= addr < self.MEMORY_SIZE:
            self.registers['MAR'] = addr
            self.registers['MBR'] = val
            self.cache.write(addr, val)

    def step(self):
        if self.halted: return

        pc = self.registers['PC']
        if pc >= self.MEMORY_SIZE:
            self.halted = True
            return

        self.micro_log.clear()
        
        # --- FETCH ---
        self.micro_log.append(f"[FETCH] MAR <- PC ({pc}); RD;")
        instruction = self._read_mem(pc)
        self.micro_log.append(f"[FETCH] PC <- PC + 1; IR <- MBR ({instruction});")
        self.registers['IR'] = instruction
        self.registers['PC'] += 1
        
        opcode_4 = (instruction >> 12) & 0xF
        operand_12 = instruction & 0xFFF
        
        # --- DECODE & EXECUTE ---
        if opcode_4 == 0x0: # LODD
            self.micro_log.append(f"[LODD] MAR <- {operand_12}; RD;")
            val = self._read_mem(operand_12)
            self.registers['AC'] = val
            self.micro_log.append(f"[LODD] AC <- MBR ({val});")
            
        elif opcode_4 == 0x1: # STOD
            val = self.registers['AC']
            self._write_mem(operand_12, val)
            self.micro_log.append(f"[STOD] MAR <- {operand_12}; MBR <- AC ({val}); WR (Cache);")
            
        elif opcode_4 == 0x2: # ADDD
            val = self._read_mem(operand_12)
            # Aritmética mantendo 16 bits unsigned para armazenamento
            res = (self.registers['AC'] + val) & 0xFFFF
            self.registers['AC'] = res
            self.micro_log.append(f"[ADDD] AC <- AC + MBR ({res});")
            
        elif opcode_4 == 0x3: # SUBD
            val = self._read_mem(operand_12)
            # Subtração com wrapping de 16 bits
            res = (self.registers['AC'] - val) & 0xFFFF
            self.registers['AC'] = res
            self.micro_log.append(f"[SUBD] AC <- AC - MBR ({res});")
            
        elif opcode_4 == 0x4: # JPOS
            # Conversão para Signed para a lógica de comparação
            ac_signed = self.registers['AC']
            if ac_signed > 32767: ac_signed -= 65536
            
            if ac_signed >= 0:
                self.registers['PC'] = operand_12
                self.micro_log.append(f"[JPOS] AC >= 0. PC <- {operand_12}")
            else:
                self.micro_log.append(f"[JPOS] AC < 0. Salto ignorado.")

        elif opcode_4 == 0x5: # JZER
            if self.registers['AC'] == 0:
                self.registers['PC'] = operand_12
                self.micro_log.append(f"[JZER] AC == 0. PC <- {operand_12}")
            else:
                self.micro_log.append(f"[JZER] AC != 0. Salto ignorado.")
                
        elif opcode_4 == 0x6: # JUMP
            self.registers['PC'] = operand_12
            self.micro_log.append(f"[JUMP] PC <- {operand_12}")
            
        elif opcode_4 == 0x7: # LOCO
            self.registers['AC'] = operand_12
            self.micro_log.append(f"[LOCO] AC <- {operand_12}")
            
        elif opcode_4 == 0x8: # LODL
            addr = (self.registers['SP'] + operand_12) & 0xFFFF
            val = self._read_mem(addr)
            self.registers['AC'] = val
            self.micro_log.append(f"[LODL] MAR <- SP + {operand_12}; RD; AC <- MBR")
            
        elif opcode_4 == 0x9: # STOL
            addr = (self.registers['SP'] + operand_12) & 0xFFFF
            val = self.registers['AC']
            self._write_mem(addr, val)
            self.micro_log.append(f"[STOL] MAR <- SP + {operand_12}; MBR <- AC; WR")
            
        elif opcode_4 == 0xA: # ADDL
            addr = (self.registers['SP'] + operand_12) & 0xFFFF
            val = self._read_mem(addr)
            self.registers['AC'] = (self.registers['AC'] + val) & 0xFFFF
            self.micro_log.append(f"[ADDL] AC <- AC + Mem[SP+{operand_12}]")
            
        elif opcode_4 == 0xB: # SUBL
            addr = (self.registers['SP'] + operand_12) & 0xFFFF
            val = self._read_mem(addr)
            self.registers['AC'] = (self.registers['AC'] - val) & 0xFFFF
            self.micro_log.append(f"[SUBL] AC <- AC - Mem[SP+{operand_12}]")
            
        elif opcode_4 == 0xC: # JNEG
            ac_signed = self.registers['AC']
            if ac_signed > 32767: ac_signed -= 65536
            
            if ac_signed < 0:
                self.registers['PC'] = operand_12
                self.micro_log.append(f"[JNEG] AC < 0. PC <- {operand_12}")
            else:
                self.micro_log.append(f"[JNEG] Salto ignorado.")
                
        elif opcode_4 == 0xD: # JNZE
            if self.registers['AC'] != 0:
                self.registers['PC'] = operand_12
                self.micro_log.append(f"[JNZE] AC != 0. PC <- {operand_12}")
            else:
                self.micro_log.append(f"[JNZE] Salto ignorado.")
                
        elif opcode_4 == 0xE: # CALL
            sp = (self.registers['SP'] - 1) & 0xFFFF
            self.registers['SP'] = sp
            self._write_mem(sp, self.registers['PC'])
            self.registers['PC'] = operand_12
            self.micro_log.append(f"[CALL] SP<-SP-1; Mem[SP]<-PC; PC<-{operand_12}")
            
        elif opcode_4 == 0xF: # Instruções Especiais
            if (instruction >> 8) == 0xFC: # INSP
                y = instruction & 0xFF
                self.registers['SP'] = (self.registers['SP'] + y) & 0xFFFF
                self.micro_log.append(f"[INSP] SP <- SP + {y}")
            elif (instruction >> 8) == 0xFE: # DESP
                y = instruction & 0xFF
                self.registers['SP'] = (self.registers['SP'] - y) & 0xFFFF
                self.micro_log.append(f"[DESP] SP <- SP - {y}")
            
            # --- IMPLEMENTAÇÃO DE PSHI e POPI ---
            elif instruction == 0xF000: # PSHI (Push Indirect)
                addr = self.registers['AC']
                val = self._read_mem(addr)
                sp = (self.registers['SP'] - 1) & 0xFFFF
                self.registers['SP'] = sp
                self._write_mem(sp, val)
                self.micro_log.append(f"[PSHI] Push Indirect: Stack <- Mem[AC:{addr}] ({val})")

            elif instruction == 0xF200: # POPI (Pop Indirect)
                sp = self.registers['SP']
                val = self._read_mem(sp)
                addr = self.registers['AC']
                self._write_mem(addr, val)
                self.registers['SP'] = (sp + 1) & 0xFFFF
                self.micro_log.append(f"[POPI] Pop Indirect: Mem[AC:{addr}] <- Stack ({val})")
            # ------------------------------------

            elif instruction == 0xF800: # RETN
                sp = self.registers['SP']
                ret_addr = self._read_mem(sp)
                self.registers['PC'] = ret_addr
                self.registers['SP'] = (sp + 1) & 0xFFFF
                self.micro_log.append("[RETN] PC <- Mem[SP]; SP <- SP + 1")
            elif instruction == 0xFA00: # SWAP
                temp = self.registers['AC']
                self.registers['AC'] = self.registers['SP']
                self.registers['SP'] = temp
                self.micro_log.append("[SWAP] AC <-> SP")
            elif instruction == 0xF400: # PUSH
                sp = (self.registers['SP'] - 1) & 0xFFFF
                self.registers['SP'] = sp
                self._write_mem(sp, self.registers['AC'])
                self.micro_log.append("[PUSH] SP<-SP-1; Mem[SP] <- AC")
            elif instruction == 0xF600: # POP
                sp = self.registers['SP']
                val = self._read_mem(sp)
                self.registers['AC'] = val
                self.registers['SP'] = (sp + 1) & 0xFFFF
                self.micro_log.append("[POP] AC <- Mem[SP]; SP<-SP+1")
            
            # FLUSH NO HALT
            elif instruction == 0xFFFF: # HALT
                self.halted = True
                self.cache.flush_all() # Força a escrita da cache na RAM
                self.micro_log.append("[HALT] Execução finalizada. Cache FLUSHED para RAM.")
            
            else:
                self.micro_log.append(f"Instrução Desconhecida: {hex(instruction)}")