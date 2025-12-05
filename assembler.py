class MIC1Assembler:
    def __init__(self):
        # Mapeamento dos mnemônicos para seus opcodes base
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
        
        # --- PASSADA 1: Mapeamento de Labels ---
        # Tivemos que fazer duas passadas porque se o label estiver mais pra frente
        # no código (forward reference), a gente não sabe o endereço dele na primeira leitura.
        labels = {}
        instructions = []
        address_counter = 0
        
        for line in raw_lines:
            # Limpeza básica (tira comentários e espaços)
            clean = line.split(';')[0].split('#')[0].strip()
            if not clean:
                continue
            
            # Tratamento de Labels (ex: "loop:")
            if ':' in clean:
                label_part, rest = clean.split(':', 1)
                label_name = label_part.strip()
                labels[label_name] = address_counter # Salva onde o label aponta
                
                rest = rest.strip()
                if rest: # Se tiver instrução na mesma linha do label
                    instructions.append(rest)
                    address_counter += 1
            else:
                instructions.append(clean)
                address_counter += 1

        # --- PASSADA 2: Geração do Binário ---
        binary_code = []
        errors = []
        
        for i, line in enumerate(instructions):
            parts = line.split()
            mnemonic = parts[0].upper()
            
            # Checa se é uma instrução válida
            if mnemonic in self.opcodes:
                base_opcode = self.opcodes[mnemonic]
                
                # Regra: OpCodes de 0x0 a 0xE precisam de argumento (operandos).
                # INSP e DESP também precisam.
                needs_operand = (base_opcode >> 12) <= 0xE or mnemonic in ['INSP', 'DESP']
                
                if needs_operand:
                    if len(parts) < 2:
                        errors.append(f"Erro na linha {i}: '{mnemonic}' precisa de um valor ou label.")
                        continue
                    
                    op_str = parts[1]
                    val = 0
                    
                    # Resolve o operando: pode ser um Label salvo na Passada 1 ou um número direto
                    if op_str in labels:
                        val = labels[op_str]
                    else:
                        try:
                            val = int(op_str)
                        except ValueError:
                            errors.append(f"Erro: Não entendi o operando '{op_str}'. Label não existe?")
                            continue
                    
                    # Bitwise OR para juntar o opcode com o operando
                    if mnemonic in ['INSP', 'DESP']:
                        final_instr = base_opcode | (val & 0xFF) # Apenas 8 bits
                    else:
                        final_instr = base_opcode | (val & 0xFFF) # 12 bits padrão
                    
                    binary_code.append(final_instr)
                else:
                    # Instruções "sozinhas" (HALT, RETN, etc)
                    binary_code.append(base_opcode)

            # Se não for instrução, pode ser dado cru (ex: variáveis no final do código)
            else:
                try:
                    val = int(mnemonic)
                    binary_code.append(val & 0xFFFF)
                except ValueError:
                    # Tenta ver se é um label usado como ponteiro
                    if mnemonic in labels:
                        binary_code.append(labels[mnemonic])
                    else:
                        errors.append(f"Erro: Comando desconhecido '{mnemonic}'")

        return binary_code, errors