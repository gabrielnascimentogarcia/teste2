class MIC1Assembler:
    def __init__(self):
        self.opcodes = {
            'LODD': 0x0000, 'STOD': 0x1000, 'ADDD': 0x2000, 'SUBD': 0x3000,
            'JPOS': 0x4000, 'JZER': 0x5000, 'JUMP': 0x6000, 'LOCO': 0x7000,
            'LODL': 0x8000, 'STOL': 0x9000, 'ADDL': 0xA000, 'SUBL': 0xB000,
            'JNEG': 0xC000, 'JNZE': 0xD000, 'CALL': 0xE000,
            'PSHI': 0xF000, 'POPI': 0xF200, 'PUSH': 0xF400, 'POP': 0xF600,
            'RETN': 0xF800, 'SWAP': 0xFA00, 'INSP': 0xFC00, 'DESP': 0xFE00,
            'HALT': 0xFFFF
        }

    def compile(self, text):
        raw_lines = text.split('\n')
        
        # --- PASSADA 1: Identificar Labels e Limpar Código ---
        labels = {}
        instructions = []
        address_counter = 0
        
        for line in raw_lines:
            # Remove comentários e espaços
            clean = line.split(';')[0].split('#')[0].strip()
            if not clean:
                continue
            
            # Verifica se há definição de label (ex: "inicio:" ou "loop: LODD 5")
            if ':' in clean:
                label_part, rest = clean.split(':', 1)
                label_name = label_part.strip()
                labels[label_name] = address_counter
                
                rest = rest.strip()
                if rest: # Se houver instrução na mesma linha do label
                    instructions.append(rest)
                    address_counter += 1
            else:
                instructions.append(clean)
                address_counter += 1

        # --- PASSADA 2: Gerar Código Binário ---
        binary_code = []
        errors = []
        
        for i, line in enumerate(instructions):
            parts = line.split()
            mnemonic = parts[0].upper()
            
            # Caso 1: É uma Instrução
            if mnemonic in self.opcodes:
                base_opcode = self.opcodes[mnemonic]
                
                # Verifica se precisa de operando (0x0...0xE e INSP/DESP)
                needs_operand = (base_opcode >> 12) <= 0xE or mnemonic in ['INSP', 'DESP']
                
                if needs_operand:
                    if len(parts) < 2:
                        errors.append(f"Erro: '{mnemonic}' requer operando")
                        continue
                    
                    op_str = parts[1]
                    val = 0
                    
                    # Tenta resolver o operando (pode ser Label ou Número)
                    if op_str in labels:
                        val = labels[op_str]
                    else:
                        try:
                            val = int(op_str)
                        except ValueError:
                            errors.append(f"Erro: Operando '{op_str}' inválido ou label não encontrado")
                            continue
                    
                    # Monta a instrução final
                    if mnemonic in ['INSP', 'DESP']:
                        final_instr = base_opcode | (val & 0xFF)
                    else:
                        final_instr = base_opcode | (val & 0xFFF)
                    
                    binary_code.append(final_instr)
                else:
                    # Instrução sem operando (ex: HALT, PUSH, RETN)
                    binary_code.append(base_opcode)

            # Caso 2: É apenas dado (número)
            else:
                try:
                    val = int(mnemonic)
                    binary_code.append(val & 0xFFFF)
                except ValueError:
                    # Tenta ver se é um label usado como dado (ex: ponteiro)
                    if mnemonic in labels:
                        binary_code.append(labels[mnemonic])
                    else:
                        errors.append(f"Erro: Instrução desconhecida '{mnemonic}'")

        return binary_code, errors