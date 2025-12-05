import random

# Classe que representa uma linha individual da Cache
# Decidimos manter simples com tag, bit de validade e o bit dirty para write-back
class CacheLine:
    def __init__(self, block_size):
        self.valid = False  # Indica se a linha tem dados úteis
        self.tag = 0        # Tag para identificação do bloco de memória
        self.dirty = False  # Flag para política de Write-Back (modificado na cache mas não na RAM)
        self.data = [0] * block_size
        self.last_access = 0 # Preparado para LRU futuro, se der tempo de implementar

# Implementação da estrutura de Cache
# Optamos por mapeamento direto para simplificar a lógica de substituição
class Cache:
    def __init__(self, memory_ref, num_lines=8, block_size=4):
        self.memory_ref = memory_ref # Referência direta à memória principal (RAM)
        self.num_lines = num_lines
        self.block_size = block_size
        # Inicializa as linhas vazias
        self.lines = [CacheLine(block_size) for _ in range(num_lines)]
        
        # Contadores para estatísticas de desempenho
        self.hits = 0
        self.misses = 0
        self.log = [] # Log interno para debug na interface

    # Calcula o índice da linha na cache (Mapeamento)
    def _get_line_index(self, address):
        return (address // self.block_size) % self.num_lines

    # Extrai a tag do endereço
    def _get_tag(self, address):
        return address // (self.block_size * self.num_lines)

    # Encontra o endereço inicial do bloco na RAM
    def _get_block_start_address(self, address):
        return (address // self.block_size) * self.block_size

    # Lógica de leitura da Cache
    def read(self, address):
        line_idx = self._get_line_index(address)
        tag = self._get_tag(address)
        offset = address % self.block_size
        
        line = self.lines[line_idx]

        # Verifica se deu HIT (tá válido e a tag bate?)
        if line.valid and line.tag == tag:
            self.hits += 1
            self.log.append(f"Cache HIT em {address} (L{line_idx})")
            return line.data[offset]
        else:
            # Tratamento de MISS
            self.misses += 1
            self.log.append(f"Cache MISS em {address}. Buscando RAM...")
            
            # Importante: Antes de sobrescrever, verificar se precisa salvar na RAM (Write-Back)
            if line.valid and line.dirty:
                self._write_back_line(line_idx)
            
            # Traz o bloco novo da RAM para a Cache
            block_start = self._get_block_start_address(address)
            for i in range(self.block_size):
                # Verificação de limite de memória pra não estourar o array
                if block_start + i < len(self.memory_ref):
                    line.data[i] = self.memory_ref[block_start + i]
            
            # Atualiza metadados da linha
            line.valid = True
            line.tag = tag
            line.dirty = False # Acabou de vir da memória, então está limpo
            
            return line.data[offset]

    # Lógica de escrita na Cache
    def write(self, address, value):
        line_idx = self._get_line_index(address)
        tag = self._get_tag(address)
        offset = address % self.block_size
        line = self.lines[line_idx]

        # Política Write-Allocate: Se tentar escrever e não tiver na cache,
        # a gente puxa da RAM primeiro, aloca e depois modifica.
        if not (line.valid and line.tag == tag):
            self.misses += 1
            self.log.append(f"Cache WRITE MISS em {address}. Alocando...")
            
            # Se a linha antiga estava suja, salva antes
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

        # Escreve apenas na Cache e marca como Dirty (Write-Back policy)
        line.data[offset] = value
        line.dirty = True

    # Função auxiliar pra salvar linha suja na RAM
    def _write_back_line(self, line_idx):
        line = self.lines[line_idx]
        # Recalcula o endereço original baseado na tag
        old_block_addr = (line.tag * self.num_lines * self.block_size) + (line_idx * self.block_size)
        
        self.log.append(f"Write-Back: Salvando Bloco {old_block_addr} na RAM")
        
        for i in range(self.block_size):
            if old_block_addr + i < len(self.memory_ref):
                self.memory_ref[old_block_addr + i] = line.data[i]
        
        line.dirty = False # Agora tá sincronizado

    # Chamado pelo HALT para garantir que nada se perca na cache
    def flush_all(self):
        flushed_count = 0
        for i in range(self.num_lines):
            if self.lines[i].valid and self.lines[i].dirty:
                self._write_back_line(i)
                flushed_count += 1
        if flushed_count > 0:
            self.log.append(f"FLUSH: {flushed_count} blocos sincronizados com a RAM.")

# Simulação do Hardware principal
class MIC1Hardware:
    def __init__(self):
        self.MEMORY_SIZE = 4096
        self.memory = [0] * self.MEMORY_SIZE
        
        # ARQUITETURA ESCOLHIDA: Harvard (Caches separadas para Instr e Dados)
        # Isso facilita a visualização na interface gráfica, separando o acesso de fetch do acesso de operando.
        self.inst_cache = Cache(self.memory, num_lines=8, block_size=4)
        self.data_cache = Cache(self.memory, num_lines=8, block_size=4)

        # Inicialização dos registradores
        self.registers = {
            'PC': 0, 'AC': 0, 'SP': 4095, # Stack começa no topo
            'IR': 0, 'TIR': 0, 'MAR': 0, 'MBR': 0,
            'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0 
        }
        self.halted = False
        self.micro_log = [] # Log das microoperações para mostrar passo a passo

    # Reinicia o estado da máquina (botão Reset da UI)
    def reset(self):
        self.memory = [0] * self.MEMORY_SIZE
        # Recria as caches zeradas
        self.inst_cache = Cache(self.memory, num_lines=8, block_size=4)
        self.data_cache = Cache(self.memory, num_lines=8, block_size=4)
        
        self.registers = {k: 0 for k in self.registers}
        self.registers['SP'] = 4095
        self.halted = False
        self.micro_log = []

    # Carrega o binário gerado pelo assembler direto na memória
    def load_program(self, program_data):
        self.reset()
        for i, value in enumerate(program_data):
            if i < self.MEMORY_SIZE:
                self.memory[i] = value
                
    # Helper para buscar instrução (Usa cache de instrução)
    def _fetch_instruction(self, addr):
        if 0 <= addr < self.MEMORY_SIZE:
            self.registers['MAR'] = addr
            val = self.inst_cache.read(addr)
            self.registers['MBR'] = val
            return val
        return 0

    # Helper para ler dados (Usa cache de dados)
    def _read_data(self, addr):
        if 0 <= addr < self.MEMORY_SIZE:
            self.registers['MAR'] = addr
            val = self.data_cache.read(addr)
            self.registers['MBR'] = val
            return val
        return 0

    # Helper para escrever dados (Usa cache de dados)
    def _write_data(self, addr, val):
        if 0 <= addr < self.MEMORY_SIZE:
            self.registers['MAR'] = addr
            self.registers['MBR'] = val
            self.data_cache.write(addr, val)

    # Executa um ciclo completo (Fetch -> Decode -> Execute)
    # Simplificamos as microinstruções em um único passo lógico para fins de simulação
    def step(self):
        if self.halted: return

        pc = self.registers['PC']
        if pc >= self.MEMORY_SIZE:
            self.halted = True
            return

        self.micro_log.clear()
        
        # --- ETAPA 1: FETCH ---
        self.micro_log.append(f"[FETCH] MAR <- PC ({pc}); RD (I-Cache);")
        instruction = self._fetch_instruction(pc)
        self.micro_log.append(f"[FETCH] PC <- PC + 1; IR <- MBR ({instruction});")
        self.registers['IR'] = instruction
        self.registers['PC'] += 1
        
        # Separa Opcode e Operando
        opcode_4 = (instruction >> 12) & 0xF
        operand_12 = instruction & 0xFFF
        
        # --- ETAPA 2: DECODE & EXECUTE ---
        # Implementação do Instruction Set
        
        if opcode_4 == 0x0: # LODD - Carrega direto do endereço
            self.micro_log.append(f"[LODD] MAR <- {operand_12}; RD (D-Cache);")
            val = self._read_data(operand_12)
            self.registers['AC'] = val
            self.micro_log.append(f"[LODD] AC <- MBR ({val});")
            
        elif opcode_4 == 0x1: # STOD - Salva acumulador na memória
            val = self.registers['AC']
            self._write_data(operand_12, val)
            self.micro_log.append(f"[STOD] MAR <- {operand_12}; MBR <- AC ({val}); WR (D-Cache);")
            
        elif opcode_4 == 0x2: # ADDD
            val = self._read_data(operand_12)
            # Mascara 0xFFFF para garantir 16 bits
            res = (self.registers['AC'] + val) & 0xFFFF
            self.registers['AC'] = res
            self.micro_log.append(f"[ADDD] AC <- AC + MBR ({res});")
            
        elif opcode_4 == 0x3: # SUBD
            val = self._read_data(operand_12)
            res = (self.registers['AC'] - val) & 0xFFFF
            self.registers['AC'] = res
            self.micro_log.append(f"[SUBD] AC <- AC - MBR ({res});")
            
        elif opcode_4 == 0x4: # JPOS - Pulo condicional
            # Conversão rápida para signed pra checar positivo
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
                
        elif opcode_4 == 0x6: # JUMP - Incondicional
            self.registers['PC'] = operand_12
            self.micro_log.append(f"[JUMP] PC <- {operand_12}")
            
        elif opcode_4 == 0x7: # LOCO - Carrega constante (0-4095)
            self.registers['AC'] = operand_12
            self.micro_log.append(f"[LOCO] AC <- {operand_12}")
            
        elif opcode_4 == 0x8: # LODL - Load Local (relativo à pilha)
            addr = (self.registers['SP'] + operand_12) & 0xFFFF
            val = self._read_data(addr)
            self.registers['AC'] = val
            self.micro_log.append(f"[LODL] MAR <- SP + {operand_12}; RD; AC <- MBR")
            
        elif opcode_4 == 0x9: # STOL
            addr = (self.registers['SP'] + operand_12) & 0xFFFF
            val = self.registers['AC']
            self._write_data(addr, val)
            self.micro_log.append(f"[STOL] MAR <- SP + {operand_12}; MBR <- AC; WR")
            
        elif opcode_4 == 0xA: # ADDL
            addr = (self.registers['SP'] + operand_12) & 0xFFFF
            val = self._read_data(addr)
            self.registers['AC'] = (self.registers['AC'] + val) & 0xFFFF
            self.micro_log.append(f"[ADDL] AC <- AC + Mem[SP+{operand_12}]")
            
        elif opcode_4 == 0xB: # SUBL
            addr = (self.registers['SP'] + operand_12) & 0xFFFF
            val = self._read_data(addr)
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
                
        elif opcode_4 == 0xE: # CALL - Procedimentos
            sp = (self.registers['SP'] - 1) & 0xFFFF
            self.registers['SP'] = sp
            self._write_data(sp, self.registers['PC']) # Salva endereço de retorno
            self.registers['PC'] = operand_12
            self.micro_log.append(f"[CALL] SP<-SP-1; Mem[SP]<-PC; PC<-{operand_12}")
            
        elif opcode_4 == 0xF: # Instruções estendidas / Operações de Pilha
            high_byte = instruction >> 8
            
            if high_byte == 0xFC: # INSP
                y = instruction & 0xFF
                self.registers['SP'] = (self.registers['SP'] + y) & 0xFFFF
                self.micro_log.append(f"[INSP] SP <- SP + {y}")

            elif high_byte == 0xFE: # DESP
                y = instruction & 0xFF
                self.registers['SP'] = (self.registers['SP'] - y) & 0xFFFF
                self.micro_log.append(f"[DESP] SP <- SP - {y}")
            
            elif instruction == 0xF000: # PSHI (Indireto)
                addr = self.registers['AC']
                val = self._read_data(addr)
                sp = (self.registers['SP'] - 1) & 0xFFFF
                self.registers['SP'] = sp
                self._write_data(sp, val)
                self.micro_log.append(f"[PSHI] Push Indirect: Stack <- Mem[AC:{addr}] ({val})")

            elif instruction == 0xF200: # POPI (Indireto)
                sp = self.registers['SP']
                val = self._read_data(sp)
                addr = self.registers['AC']
                self._write_data(addr, val)
                self.registers['SP'] = (sp + 1) & 0xFFFF
                self.micro_log.append(f"[POPI] Pop Indirect: Mem[AC:{addr}] <- Stack ({val})")

            elif instruction == 0xF800: # RETN
                sp = self.registers['SP']
                ret_addr = self._read_data(sp)
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
                self._write_data(sp, self.registers['AC'])
                self.micro_log.append("[PUSH] SP<-SP-1; Mem[SP] <- AC")
                
            elif instruction == 0xF600: # POP
                sp = self.registers['SP']
                val = self._read_data(sp)
                self.registers['AC'] = val
                self.registers['SP'] = (sp + 1) & 0xFFFF
                self.micro_log.append("[POP] AC <- Mem[SP]; SP<-SP+1")
            
            elif instruction == 0xFFFF: # HALT
                self.halted = True
                # Garante que dados na cache (sujos) vão pra memória ao desligar
                self.data_cache.flush_all() 
                self.inst_cache.flush_all() 
                self.micro_log.append("[HALT] Execução finalizada. Caches FLUSHED.")
            
            else:
                self.micro_log.append(f"Instrução Desconhecida: {hex(instruction)}")