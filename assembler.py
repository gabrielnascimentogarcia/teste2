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
        lines = text.split('\n')
        binary_code = []
        errors = []
        
        # 1. Primeira passada (opcional, para labels futuros)
        # Aqui simplificamos para tradução direta linha a linha conforme MIC-1 padrão
        
        for i, line in enumerate(lines):
            line_num = i + 1
            # Remove comentários e espaços extras
            clean_line = line.split(';')[0].split('#')[0].strip()
            
            if not clean_line:
                continue

            parts = clean_line.split()
            mnemonic = parts[0].upper()

            # Caso seja apenas um número (dado puro)
            if mnemonic not in self.opcodes:
                try:
                    val = int(mnemonic)
                    binary_code.append(val & 0xFFFF)
                    continue
                except ValueError:
                    # Pode ser um label ou erro, vamos assumir erro por enquanto nesta versão simples
                    errors.append(f"Linha {line_num}: Instrução inválida '{mnemonic}'")
                    continue

            base_opcode = self.opcodes[mnemonic]
            
            # Instruções que precisam de operando (0x0 a 0xE e INSP/DESP)
            needs_operand = (base_opcode >> 12) <= 0xE or mnemonic in ['INSP', 'DESP']
            
            if needs_operand:
                if len(parts) < 2:
                    errors.append(f"Linha {line_num}: '{mnemonic}' requer operando")
                    continue
                try:
                    operand = int(parts[1])
                    if mnemonic in ['INSP', 'DESP']:
                        final_instr = base_opcode | (operand & 0xFF)
                    else:
                        final_instr = base_opcode | (operand & 0xFFF)
                    binary_code.append(final_instr)
                except ValueError:
                    errors.append(f"Linha {line_num}: Operando inválido '{parts[1]}'")
            else:
                binary_code.append(base_opcode)

        return binary_code, errors