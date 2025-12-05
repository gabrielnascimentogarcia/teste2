import random

#Linha individual da Cache
#Possui tag, bit de validade e o dirty-bit para copy-back, como aprendido em sala
class CacheLine:
    def __init__(self, block_size):
        self.valid = False  #Indica se a linha tem dados válidos
        self.tag = 0        #Identificação do bloco de memória
        self.dirty = False  #Para o copy-back (modificado na cache, e não na MP)
        self.data = [0]*block_size

#Implementação da estrutura de Cache (usamos mapeamento direto, para facilitar)
class Cache:
    def __init__(self, memory_ref, num_lines=8, block_size=4):
        self.memory_ref = memory_ref #Referência p/a RAM
        self.num_lines = num_lines
        self.block_size = block_size
        #Inicializa as linhas vazias
        self.lines = [CacheLine(block_size) for _ in range(num_lines)]
        
        #Contadores de desempenho
        self.hits = 0
        self.misses = 0
        self.log = [] #Log interno p/ debug na interface

    #Calcula o índice da linha na cache
    def _get_line_index(self, address):
        return (address // self.block_size) % self.num_lines

    #Extrai a tag do endereço
    def _get_tag(self, address):
        return address // (self.block_size * self.num_lines)

    #Encontra o endereço inicial do bloco na RAM
    def _get_block_start_address(self, address):
        return (address // self.block_size) * self.block_size

    #Lógica de leitura da cache
    def read(self, address):
        line_idx = self._get_line_index(address)
        tag = self._get_tag(address)
        offset = address % self.block_size
        
        line = self.lines[line_idx]

        #Verifica se deu cache hit (se está válido e a tag bate com a esperada)
        if line.valid and line.tag == tag:
            self.hits += 1
            self.log.append(f"Cache HIT em {address} (L{line_idx})")
            return line.data[offset]
        else:
            #Caso contrário, é cache miss
            self.misses += 1
            self.log.append(f"Cache MISS em {address}. Buscando RAM...")
            
            # Importante: Antes de sobrescrever, verificar se precisa salvar na RAM (Write-Back)
            if line.valid and line.dirty:
                self._write_back_line(line_idx)
            
            #Traz o bloco novo da RAM para a nossa cache
            block_start = self._get_block_start_address(address)
            for i in range(self.block_size):
                # Verificação de limite de memória pra não estourar o array
                if block_start + i < len(self.memory_ref):
                    line.data[i] = self.memory_ref[block_start + i]
            
            #Atualiza metadados da linha
            line.valid = True
            line.tag = tag
            line.dirty = False # Acabou de vir da memória, então está limpo
            
            return line.data[offset]

    #Lógica de escrita na Cache
    def write(self, address, value):
        line_idx = self._get_line_index(address)
        tag = self._get_tag(address)
        offset = address % self.block_size
        line = self.lines[line_idx]

        #Se tentar escrever e não tiver na cache, puxamos da RAM primeiro, alocamos e depois modificamos.
        if not (line.valid and line.tag == tag):
            self.misses += 1
            self.log.append(f"Cache WRITE MISS em {address}. Alocando...")
            
            #Se a linha antiga estava suja, salva antes
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

        #Escreve apenas na cache e faz a marcação do dirty-bit
        line.data[offset] = value
        line.dirty = True

    #Função auxiliar p/ salvar linha suja na MP
    def _write_back_line(self, line_idx):
        line = self.lines[line_idx]
        #Recalcula o endereço original baseado na tag
        old_block_addr = (line.tag * self.num_lines * self.block_size) + (line_idx * self.block_size)
        
        self.log.append(f"Write-Back: Salvando Bloco {old_block_addr} na RAM")
        
        for i in range(self.block_size):
            if old_block_addr + i < len(self.memory_ref):
                self.memory_ref[old_block_addr + i] = line.data[i]
        
        line.dirty = False # Agora tá sincronizado

    #Chamado pelo HALT para garantir que nada se perca na cache
    def flush_all(self):
        flushed_count = 0
        for i in range(self.num_lines):
            if self.lines[i].valid and self.lines[i].dirty:
                self._write_back_line(i)
                flushed_count += 1
        if flushed_count > 0:
            self.log.append(f"FLUSH: {flushed_count} blocos sincronizados com a RAM.")

#Simulação do hardware principal
class MIC1Hardware:
    def __init__(self):
        self.MEMORY_SIZE = 4096
        self.memory = [0] * self.MEMORY_SIZE
        
        #Escolhemos usar a arquitetura de Harvard, que consiste na divisão em cache de instrução e cache de dados
        #Isso ajuda a facilitar a visualização na interface gráfica, separando o acesso de fetch do acesso de operando.
        self.inst_cache = Cache(self.memory, num_lines=8, block_size=4)
        self.data_cache = Cache(self.memory, num_lines=8, block_size=4)

        #Inicialização dos registradores
        self.registers = {
            'PC': 0, 'AC': 0, 'SP': 4095, #A pilha começa apontando para o topo
            'IR': 0, 'TIR': 0, 'MAR': 0, 'MBR': 0,
            'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0 
        }
        self.halted = False
        self.micro_log = [] #Log das microoperações p/ mostrar passo a passo

    #Reinicia o estado da máquina (botão reset)
    def reset(self):
        self.memory = [0] * self.MEMORY_SIZE
        # Recria as caches zeradas
        self.inst_cache = Cache(self.memory, num_lines=8, block_size=4)
        self.data_cache = Cache(self.memory, num_lines=8, block_size=4)
        
        self.registers = {k: 0 for k in self.registers}
        self.registers['SP'] = 4095
        self.halted = False
        self.micro_log = []

    #Carrega o binário gerado pelo assembler direto na memória
    def load_program(self, program_data):
        self.reset()
        for i, value in enumerate(program_data):
            if i < self.MEMORY_SIZE:
                self.memory[i] = value
                
    #Função para buscar instrução (cache de inst)
    def _fetch_instruction(self, addr):
        if 0 <= addr < self.MEMORY_SIZE:
            self.registers['MAR'] = addr
            val = self.inst_cache.read(addr)
            self.registers['MBR'] = val
            return val
        return 0

    #Função para ler dados (cache de dados)
    def _read_data(self, addr):
        if 0 <= addr < self.MEMORY_SIZE:
            self.registers['MAR'] = addr
            val = self.data_cache.read(addr)
            self.registers['MBR'] = val
            return val
        return 0

    #Função para escrever dados (cache de dados)
    def _write_data(self, addr, val):
        if 0 <= addr < self.MEMORY_SIZE:
            self.registers['MAR'] = addr
            self.registers['MBR'] = val
            self.data_cache.write(addr, val)

    #Executa um ciclo completo (fetch -> decode -> execute)

    def step(self):
        if self.halted: return

        pc = self.registers['PC']
        if pc >= self.MEMORY_SIZE:
            self.halted = True
            return

        self.micro_log.clear()
        
        #Etapa 1: FETCH
        self.micro_log.append(f"[FETCH] MAR <- PC ({pc}); RD (I-Cache);")
        instruction = self._fetch_instruction(pc)
        self.micro_log.append(f"[FETCH] PC <- PC + 1; IR <- MBR ({instruction});")
        self.registers['IR'] = instruction
        self.registers['PC'] += 1
        
        #Separa Opcode e Operando
        opcode_4 = (instruction >> 12) & 0b1111
        operand_12 = instruction & 0b111111111111
        
        #Etapa 2: DECODE & EXECUTE
        #Implementação do instruction set com verificação binária
        
        if opcode_4 == 0b0000: #LODD - carrega direto do endereço
            self.micro_log.append(f"[LODD] MAR <- {operand_12}; RD (D-Cache);")
            val = self._read_data(operand_12)
            self.registers['AC'] = val
            self.micro_log.append(f"[LODD] AC <- MBR ({val});")
            
        elif opcode_4 == 0b0001: #STOD - salva acumulador na memória
            val = self.registers['AC']
            self._write_data(operand_12, val)
            self.micro_log.append(f"[STOD] MAR <- {operand_12}; MBR <- AC ({val}); WR (D-Cache);")
            
        elif opcode_4 == 0b0010: #ADDD
            val = self._read_data(operand_12)
            # Mascara 16 bits
            res = (self.registers['AC'] + val) & 0b1111111111111111
            self.registers['AC'] = res
            self.micro_log.append(f"[ADDD] AC <- AC + MBR ({res});")
            
        elif opcode_4 == 0b0011: #SUBD
            val = self._read_data(operand_12)
            res = (self.registers['AC'] - val) & 0b1111111111111111
            self.registers['AC'] = res
            self.micro_log.append(f"[SUBD] AC <- AC - MBR ({res});")
            
        elif opcode_4 == 0b0100: #JPOS - pulo condicional
            # Conversão rápida para signed pra checar positivo
            ac_signed = self.registers['AC']
            if ac_signed > 32767: ac_signed -= 65536
            
            if ac_signed >= 0:
                self.registers['PC'] = operand_12
                self.micro_log.append(f"[JPOS] AC >= 0. PC <- {operand_12}")
            else:
                self.micro_log.append(f"[JPOS] AC < 0. Salto ignorado.")

        elif opcode_4 == 0b0101: #JZER
            if self.registers['AC'] == 0:
                self.registers['PC'] = operand_12
                self.micro_log.append(f"[JZER] AC == 0. PC <- {operand_12}")
            else:
                self.micro_log.append(f"[JZER] AC != 0. Salto ignorado.")
                
        elif opcode_4 == 0b0110: #JUMP - incondicional
            self.registers['PC'] = operand_12
            self.micro_log.append(f"[JUMP] PC <- {operand_12}")
            
        elif opcode_4 == 0b0111: #LOCO - carrega constante
            self.registers['AC'] = operand_12
            self.micro_log.append(f"[LOCO] AC <- {operand_12}")
            
        elif opcode_4 == 0b1000: #LODL - load local (relativo à pilha)
            addr = (self.registers['SP'] + operand_12) & 0b1111111111111111
            val = self._read_data(addr)
            self.registers['AC'] = val
            self.micro_log.append(f"[LODL] MAR <- SP + {operand_12}; RD; AC <- MBR")
            
        elif opcode_4 == 0b1001: #STOL
            addr = (self.registers['SP'] + operand_12) & 0b1111111111111111
            val = self.registers['AC']
            self._write_data(addr, val)
            self.micro_log.append(f"[STOL] MAR <- SP + {operand_12}; MBR <- AC; WR")
            
        elif opcode_4 == 0b1010: #ADDL
            addr = (self.registers['SP'] + operand_12) & 0b1111111111111111
            val = self._read_data(addr)
            self.registers['AC'] = (self.registers['AC'] + val) & 0b1111111111111111
            self.micro_log.append(f"[ADDL] AC <- AC + Mem[SP+{operand_12}]")
            
        elif opcode_4 == 0b1011: #SUBL
            addr = (self.registers['SP'] + operand_12) & 0b1111111111111111
            val = self._read_data(addr)
            self.registers['AC'] = (self.registers['AC'] - val) & 0b1111111111111111
            self.micro_log.append(f"[SUBL] AC <- AC - Mem[SP+{operand_12}]")
            
        elif opcode_4 == 0b1100: #JNEG
            ac_signed = self.registers['AC']
            if ac_signed > 32767: ac_signed -= 65536
            if ac_signed < 0:
                self.registers['PC'] = operand_12
                self.micro_log.append(f"[JNEG] AC < 0. PC <- {operand_12}")
            else:
                self.micro_log.append(f"[JNEG] Salto ignorado.")
                
        elif opcode_4 == 0b1101: #JNZE
            if self.registers['AC'] != 0:
                self.registers['PC'] = operand_12
                self.micro_log.append(f"[JNZE] AC != 0. PC <- {operand_12}")
            else:
                self.micro_log.append(f"[JNZE] Salto ignorado.")
                
        elif opcode_4 == 0b1110: #CALL
            sp = (self.registers['SP'] - 1) & 0b1111111111111111
            self.registers['SP'] = sp
            self._write_data(sp, self.registers['PC']) #Salva endereço de retorno
            self.registers['PC'] = operand_12
            self.micro_log.append(f"[CALL] SP<-SP-1; Mem[SP]<-PC; PC<-{operand_12}")
            
        elif opcode_4 == 0b1111: #Instruções estendidas/ operações de pilha
            high_byte = instruction >> 8
            
            if high_byte == 0b11111100: #INSP
                y = instruction & 0b11111111
                self.registers['SP'] = (self.registers['SP'] + y) & 0b1111111111111111
                self.micro_log.append(f"[INSP] SP <- SP + {y}")

            elif high_byte == 0b11111110: #DESP
                y = instruction & 0b11111111
                self.registers['SP'] = (self.registers['SP'] - y) & 0b1111111111111111
                self.micro_log.append(f"[DESP] SP <- SP - {y}")
            
            elif instruction == 0b1111000000000000: #PSHI (push indireto)
                addr = self.registers['AC']
                val = self._read_data(addr)
                sp = (self.registers['SP'] - 1) & 0b1111111111111111
                self.registers['SP'] = sp
                self._write_data(sp, val)
                self.micro_log.append(f"[PSHI] Push Indirect: Stack <- Mem[AC:{addr}] ({val})")

            elif instruction == 0b1111001000000000: #POPI (pop indireto)
                sp = self.registers['SP']
                val = self._read_data(sp)
                addr = self.registers['AC']
                self._write_data(addr, val)
                self.registers['SP'] = (sp + 1) & 0b1111111111111111
                self.micro_log.append(f"[POPI] Pop Indirect: Mem[AC:{addr}] <- Stack ({val})")

            elif instruction == 0b1111100000000000: #RETN
                sp = self.registers['SP']
                ret_addr = self._read_data(sp)
                self.registers['PC'] = ret_addr
                self.registers['SP'] = (sp + 1) & 0b1111111111111111
                self.micro_log.append("[RETN] PC <- Mem[SP]; SP <- SP + 1")
                
            elif instruction == 0b1111101000000000: #SWAP
                temp = self.registers['AC']
                self.registers['AC'] = self.registers['SP']
                self.registers['SP'] = temp
                self.micro_log.append("[SWAP] AC <-> SP")
                
            elif instruction == 0b1111010000000000: #PUSH
                sp = (self.registers['SP'] - 1) & 0b1111111111111111
                self.registers['SP'] = sp
                self._write_data(sp, self.registers['AC'])
                self.micro_log.append("[PUSH] SP<-SP-1; Mem[SP] <- AC")
                
            elif instruction == 0b1111011000000000: #POP
                sp = self.registers['SP']
                val = self._read_data(sp)
                self.registers['AC'] = val
                self.registers['SP'] = (sp + 1) & 0b1111111111111111
                self.micro_log.append("[POP] AC <- Mem[SP]; SP<-SP+1")
            
            elif instruction == 0b1111111111111111: #HALT
                self.halted = True
                #O HALT garante que os dados na cache (sujos) vão ser atualizados na memória ao desligar o programa
                self.data_cache.flush_all() 
                self.inst_cache.flush_all() 
                self.micro_log.append("[HALT] Execução finalizada. Caches FLUSHED.")
            
            else:
                self.micro_log.append(f"Instrução Desconhecida: {bin(instruction)}")