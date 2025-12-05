class MIC1Assembler:
    def __init__(self):
        # Mapeamento dos mnemônicos para seus opcodes base
        # Agora utilizando notação binária para facilitar a correlação com a documentação (MAC I)
        self.opcodes = {
            'LODD': 0b0000000000000000, 'STOD': 0b0001000000000000, 
            'ADDD': 0b0010000000000000, 'SUBD': 0b0011000000000000,
            'JPOS': 0b0100000000000000, 'JZER': 0b0101000000000000, 
            'JUMP': 0b0110000000000000, 'LOCO': 0b0111000000000000,
            'LODL': 0b1000000000000000, 'STOL': 0b1001000000000000, 
            'ADDL': 0b1010000000000000, 'SUBL': 0b1011000000000000,
            'JNEG': 0b1100000000000000, 'JNZE': 0b1101000000000000, 
            'CALL': 0b1110000000000000,
            'PSHI': 0b1111000000000000, 'POPI': 0b1111001000000000, 
            'PUSH': 0b1111010000000000, 'POP':  0b1111011000000000,
            'RETN': 0b1111100000000000, 'SWAP': 0b1111101000000000, 
            'INSP': 0b1111110000000000, 'DESP': 0b1111111000000000,
            'HALT': 0b1111111111111111
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
                
                # Regra: OpCodes de 0000 a 1110 precisam de argumento (operandos).
                # INSP e DESP também precisam.
                needs_operand = (base_opcode >> 12) <= 0b1110 or mnemonic in ['INSP', 'DESP']
                
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
                        final_instr = base_opcode | (val & 0b11111111) # Apenas 8 bits
                    else:
                        final_instr = base_opcode | (val & 0b111111111111) # 12 bits padrão
                    
                    binary_code.append(final_instr)
                else:
                    # Instruções "sozinhas" (HALT, RETN, etc)
                    binary_code.append(base_opcode)

            # Se não for instrução, pode ser dado cru (ex: variáveis no final do código)
            else:
                try:
                    val = int(mnemonic)
                    binary_code.append(val & 0b1111111111111111)
                except ValueError:
                    # Tenta ver se é um label usado como ponteiro
                    if mnemonic in labels:
                        binary_code.append(labels[mnemonic])
                    else:
                        errors.append(f"Erro: Comando desconhecido '{mnemonic}'")

        return binary_code, errors