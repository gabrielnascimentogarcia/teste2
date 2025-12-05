# Simulador MIC-1

Simulador da arquitetura MIC-1 com sistema de cache hierárquico. Desenvolvido como projeto acadêmico para visualização e estudo de arquitetura de computadores.

**Desenvolvedores:** Gabriel G., Iuri F., Maria Eduarda V., Marilia S., Pedro L., Yasmin M.

---

## Instalação

### Requisitos

- Python 3.7+
- Tkinter (geralmente já vem com Python)

### Rodando o projeto

```bash
git clone https://github.com/gabrielnascimentogarcia/teste2.git
cd teste2
python app.py
```

Se o Tkinter não estiver instalado:

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# macOS (Homebrew)
brew install python-tk
```

---

## Uso Básico

A interface possui três áreas principais:

**Painel Esquerdo:**
- Editor de Assembly (topo)
- Log de microinstruções (baixo)

**Painel Direito:**
- Registradores do processador
- Visualização das caches (dados e instruções)
- Tabela completa da memória RAM

### Workflow

1. Escreva código Assembly no editor
2. Clique em "Compilar & Carregar"
3. Use os controles de execução:
   - **Run**: execução contínua
   - **Ciclo**: executa uma instrução por vez
   - **Pause**: pausa execução
   - **Reset**: reinicia o estado

O slider de velocidade controla a frequência de execução (1-20 Hz).

---

## Instruction Set

### Operações de Memória

```assembly
LODD addr    ; AC ← Mem[addr]
STOD addr    ; Mem[addr] ← AC
LOCO const   ; AC ← const (0-4095)
LODL offset  ; AC ← Mem[SP + offset]
STOL offset  ; Mem[SP + offset] ← AC
```

### Aritmética

```assembly
ADDD addr    ; AC ← AC + Mem[addr]
SUBD addr    ; AC ← AC - Mem[addr]
ADDL offset  ; AC ← AC + Mem[SP + offset]
SUBL offset  ; AC ← AC - Mem[SP + offset]
```

### Controle de Fluxo

```assembly
JUMP addr    ; PC ← addr
JPOS addr    ; if (AC >= 0) PC ← addr
JZER addr    ; if (AC == 0) PC ← addr
JNEG addr    ; if (AC < 0) PC ← addr
JNZE addr    ; if (AC != 0) PC ← addr
CALL addr    ; push PC, PC ← addr
RETN         ; PC ← pop()
```

### Stack

```assembly
PUSH         ; push AC
POP          ; AC ← pop()
PSHI         ; push Mem[AC]
POPI         ; Mem[AC] ← pop()
INSP n       ; SP ← SP + n
DESP n       ; SP ← SP - n
SWAP         ; AC ↔ SP
```

### Controle

```assembly
HALT         ; para execução e faz flush das caches
```

---

## Exemplos

### Operações Básicas

```assembly
; Subtração simples
LOCO 10
STOD 10      ; Mem[10] = 10

LOCO 5
SUBD 10      ; AC = 5 - 10 = -5
STOD 11      ; Mem[11] = -5

HALT
```

### Loop com Labels

```assembly
; Contador de 0 a 5
LOCO 0
STOD 100

loop:
LODD 100
LOCO 1
ADDD 100
STOD 100
LOCO 5
SUBD 100
JPOS loop

HALT
```

### Subrotinas

```assembly
LOCO 10
CALL func
STOD 50
HALT

func:
ADDD 100
RETN

100
15
```

### Stack Operations

```assembly
LOCO 100
PUSH

LOCO 200
PUSH

LOCO 300
PUSH

POP
STOD 10     ; Mem[10] = 300

POP
STOD 11     ; Mem[11] = 200

POP
STOD 12     ; Mem[12] = 100

HALT
```

---

## Arquitetura

### Hierarquia de Memória

O simulador implementa caches separadas:

- **Cache de Instruções**: 8 linhas, blocos de 4 palavras
- **Cache de Dados**: 8 linhas, blocos de 4 palavras
- **Memória Principal**: 4096 palavras de 16 bits

### Políticas de Cache

- **Mapeamento**: Direto
- **Substituição**: Determinística (mapeamento direto)
- **Escrita**: Write-Back + Write-Allocate
- **Bloco**: 4 palavras (16 bits cada)

### Registradores

- **PC**: Program Counter
- **AC**: Accumulator
- **SP**: Stack Pointer (inicializado em 4095)
- **IR**: Instruction Register
- **MAR**: Memory Address Register
- **MBR**: Memory Buffer Register
- **TIR**: Temporary Instruction Register
- **A, B, C**: Registradores auxiliares

### Formato das Instruções (Padrão Binário)

Instruções tipo 1 (Opcodes 0000 a 1110):
```
[4 bits opcode] [12 bits operando]
Exemplo STOD: 0001 000000001010
```

Instruções tipo 2 (Opcode 1111 com subopcode):
```
[1111] [4 bits subop] [8 bits operando]
Exemplo INSP: 1111 1100 00000101
```

Instruções fixas (Opcode 1111 + extensão fixa):
```
[16 bits opcode fixo]
Exemplo HALT: 1111 1111 1111 1111
```

---

## Observações Sobre o Sistema de Cache

O comportamento da cache pode ser observado nos logs e nas tabelas de cache:

- **Valid bit**: indica se a linha contém dados válidos
- **Tag**: identifica qual bloco de memória está armazenado
- **Dirty bit**: indica se o bloco foi modificado (Write-Back)
- **Data**: array com os 4 valores do bloco

Quando o HALT é executado, todas as linhas dirty são escritas de volta na RAM (flush completo).

Loops tendem a ter alta taxa de hit após a primeira iteração, já que as instruções ficam cacheadas.

---

## Estrutura do Código

```
app.py               # Interface gráfica (Tkinter)
mic1_hardware.py     # Simulação do hardware (CPU, Cache, RAM)
assembler.py         # Compilador Assembly → Binário
```

### Compilação

O assembler faz duas passadas:
1. **Pass 1**: Mapeia labels para endereços
2. **Pass 2**: Gera código binário com labels resolvidos

Suporta comentários com `;` ou `#` e permite labels na mesma linha da instrução.

---

## Troubleshooting

**Erro: "No module named 'tkinter'"**
- Instale o pacote python3-tk conforme instruções acima

**Erro: "Label não existe"**
- Verifique se o label foi declarado com `:` (ex: `loop:`)
- Labels são case-sensitive

**Valores negativos aparecem como grandes números positivos**
- Use a coluna "Decimal (Signed)" na tabela de memória
- Internamente trabalhamos com 16 bits unsigned, mas a UI mostra a conversão

**Cache não atualiza na interface**
- Reduza a velocidade de execução
- Use modo "Ciclo" para execução passo a passo

---

## Observações

As microinstruções foram simplificadas em um único step lógico para facilitar a implementação e visualização do simulador.