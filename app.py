import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
from mic1_hardware import MIC1Hardware #módulo local
from assembler import MIC1Assembler #módulo local

#Classe principal da nossa interface gráfica
class MIC1SimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador MIC-1 Gabriel G. Iuri F. Maria Eduarda V. Marilia S. Pedro L. Yasmin M.")
        self.root.geometry("1400x800") #Resolução
        self.root.configure(bg="#2b2b2b") #Modo escuro
        
        #Configuração de estilos do tkinter
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", background="#333", foreground="white", fieldbackground="#333", font=("Consolas", 10))
        self.style.configure("Treeview.Heading", background="#555", foreground="white", font=("Arial", 10, "bold"))
        self.style.configure("TFrame", background="#2b2b2b")
        self.style.configure("TLabel", background="#2b2b2b", foreground="white")
        self.style.configure("TButton", font=("Arial", 10, "bold"))

        #Instância do hardware e do assembler
        self.cpu = MIC1Hardware()
        self.assembler = MIC1Assembler()
        self.running = False 
        self.create_widgets()
        
        #Preencher a tabela de memória
        self.init_memory_view()
        self.update_ui()

    #Função aux para converter unsigned 16-bit para signed (melhora a legibilidade na interface)
    def to_signed(self, val):
        if val > 32767:
            return val - 65536
        return val

    #Montagem do layout
    def create_widgets(self):
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        #Coluna da esquerda (editor e controles do programa)
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        ttk.Label(left_panel, text="Editor Assembly").pack(anchor="w")
        self.editor = scrolledtext.ScrolledText(left_panel, width=40, height=20, font=("Consolas", 11), bg="#1e1e1e", fg="#dcdcdc", insertbackground="white")
        self.editor.pack(fill=tk.BOTH, expand=True, pady=5)
        
        #Exemplo de código inicial para o nosso teste
        self.editor.insert(tk.END, "; Teste de Subtração e Store\nLOCO 10\nSTOD 10\n\nLOCO 5\nSUBD 10  ; 5 - 10 = -5 (Deve aparecer negativo)\nSTOD 11  ; Salva -5 em 11\nHALT     ; Deve salvar cache na RAM\n\n")

        #Botões de compilação
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Compilar & Carregar", command=self.compile_and_load).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        #Área de controle de execução
        ctrl_frame = ttk.LabelFrame(left_panel, text="Controles")
        ctrl_frame.pack(fill=tk.X, pady=10)
        
        ctrl_btns = ttk.Frame(ctrl_frame)
        ctrl_btns.pack(pady=5)
        
        ttk.Button(ctrl_btns, text="▶ Run", command=self.start_simulation, width=8).grid(row=0, column=0, padx=2)
        ttk.Button(ctrl_btns, text="⏸ Pause", command=self.pause_simulation, width=8).grid(row=0, column=1, padx=2)
        ttk.Button(ctrl_btns, text="⏭ Ciclo", command=self.step_simulation, width=8).grid(row=0, column=2, padx=2)
        ttk.Button(ctrl_btns, text="⏹ Reset", command=self.reset_simulation, width=8).grid(row=0, column=3, padx=2)

        #Controle de velocidade (clock simulado)
        speed_frame = ttk.Frame(ctrl_frame)
        speed_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(speed_frame, text="Velocidade (Hz):").pack(side=tk.LEFT)
        self.speed_scale = tk.Scale(speed_frame, from_=1, to=10, orient=tk.HORIZONTAL, bg="#2b2b2b", fg="white", highlightthickness=0)
        self.speed_scale.set(5)
        self.speed_scale.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        #Log de microinstruções
        ttk.Label(left_panel, text="Histórico de Microinstruções").pack(anchor="w", pady=(10,0))
        self.log_display = scrolledtext.ScrolledText(left_panel, height=12, font=("Consolas", 9), bg="#000", fg="#0f0")
        self.log_display.pack(fill=tk.BOTH, expand=True)

        #Coluna da direita, que contem os regs, caches, memoria,...
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        #Visualização dos registradores
        reg_frame = ttk.LabelFrame(right_panel, text="Processador (Registradores)")
        reg_frame.pack(fill=tk.X, pady=5)
        
        for i in range(5):
            reg_frame.grid_columnconfigure(i, weight=1)

        self.reg_widgets = {} 
        regs = ['PC', 'AC', 'SP', 'IR', 'MAR', 'MBR', 'TIR', 'A', 'B', 'C']
        
        #Cria os cards dos regs
        r, c = 0, 0
        for reg in regs:
            #Container estilizado
            card = tk.Frame(reg_frame, bg="#3e3e42", bd=1, relief="flat")
            card.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
            
            lbl_title = tk.Label(card, text=reg, font=("Segoe UI", 9, "bold"), bg="#3e3e42", fg="#aaaaaa")
            lbl_title.pack(pady=(5, 0))
            
            #HEX
            lbl_hex = tk.Label(card, text="0000", font=("Consolas", 14, "bold"), bg="#3e3e42", fg="#4ec9b0")
            lbl_hex.pack()
            
            #DEC
            lbl_dec = tk.Label(card, text="0", font=("Segoe UI", 8), bg="#3e3e42", fg="#dcdcdc")
            lbl_dec.pack(pady=(0, 5))
            
            self.reg_widgets[reg] = {'hex': lbl_hex, 'dec': lbl_dec}
            
            c += 1
            if c > 4: r, c = 1, 0

        #Sistema de abas para visualização das caches (dados/instrução)
        cache_container = ttk.LabelFrame(right_panel, text="Sistema de Caches")
        cache_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.cache_tabs = ttk.Notebook(cache_container)
        self.cache_tabs.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.d_cache_frame = ttk.Frame(self.cache_tabs)
        self.cache_tabs.add(self.d_cache_frame, text="Cache de DADOS")
        
        self.i_cache_frame = ttk.Frame(self.cache_tabs)
        self.cache_tabs.add(self.i_cache_frame, text="Cache de INSTRUÇÕES")
        
        cols_cache = ("Linha", "Valid", "Tag", "Dirty", "Dados (Bloco)")
        
        #Config da tabela de cache de dados
        self.d_cache_tree = ttk.Treeview(self.d_cache_frame, columns=cols_cache, show="headings", height=5)
        for col in cols_cache:
            self.d_cache_tree.heading(col, text=col)
            self.d_cache_tree.column(col, width=50, anchor="center")
        self.d_cache_tree.column("Dados (Bloco)", width=180)
        self.d_cache_tree.pack(fill=tk.BOTH, expand=True)

        #Config da tabela de cache de instruções
        self.i_cache_tree = ttk.Treeview(self.i_cache_frame, columns=cols_cache, show="headings", height=5)
        for col in cols_cache:
            self.i_cache_tree.heading(col, text=col)
            self.i_cache_tree.column(col, width=50, anchor="center")
        self.i_cache_tree.column("Dados (Bloco)", width=180)
        self.i_cache_tree.pack(fill=tk.BOTH, expand=True)

        #Memória principal (RAM)
        mem_frame = ttk.LabelFrame(right_panel, text="Memória Principal (4096 Palavras)")
        mem_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        cols_mem = ("Addr", "Binário (16b)", "Decimal (Signed)", "Hex")
        self.mem_tree = ttk.Treeview(mem_frame, columns=cols_mem, show="headings", height=15)
        self.mem_tree.heading("Addr", text="Endereço")
        self.mem_tree.heading("Binário (16b)", text="Binário")
        self.mem_tree.heading("Decimal (Signed)", text="Decimal (Signed)")
        self.mem_tree.heading("Hex", text="Hex")
        
        #Scrollbar é essencial aqui pq são 4096 linhas
        vsb = ttk.Scrollbar(mem_frame, orient="vertical", command=self.mem_tree.yview)
        self.mem_tree.configure(yscroll=vsb.set)
        self.mem_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def init_memory_view(self):
        # Cria as linhas iniciais da memória (tudo zero)
        self.mem_tree.delete(*self.mem_tree.get_children())
        for addr in range(4096):
            val = 0
            bin_s = f"{val:016b}"
            hex_s = f"{val:04X}"
            self.mem_tree.insert("", "end", iid=str(addr), values=(addr, bin_s, val, hex_s))

    def compile_and_load(self):
        code = self.editor.get("1.0", tk.END)
        # Chama nosso assembler
        binary, errors = self.assembler.compile(code)
        
        if errors:
            messagebox.showerror("Erro de Compilação", "\n".join(errors))
            return
            
        self.cpu.reset()
        self.cpu.load_program(binary)
        self.update_full_memory_view()
        self.update_ui()
        self.log("Programa compilado e carregado com sucesso.")

    def update_full_memory_view(self):
        #Atualiza a Grid da memória. 
        for addr in range(4096):
            val = self.cpu.memory[addr]
            bin_s = f"{val:016b}"
            signed_val = self.to_signed(val)
            hex_s = f"{val:04X}"
            self.mem_tree.item(str(addr), values=(addr, bin_s, signed_val, hex_s))

    def update_ui(self):
        #Atualiza valores dos registradores na tela
        for reg, widgets in self.reg_widgets.items():
            val = self.cpu.registers.get(reg, 0)
            signed_val = self.to_signed(val)
            widgets['hex'].config(text=f"{val:04X}")
            widgets['dec'].config(text=f"{signed_val}")

        self.update_full_memory_view()

        #Faz a tabela rolar até onde o PC está apontando (auto-scroll)
        pc = self.cpu.registers['PC']
        if pc < 4096:
            self.mem_tree.selection_set(str(pc))
            self.mem_tree.see(str(pc))

        #Refresh das caches
        
        #Cache de dados
        self.d_cache_tree.delete(*self.d_cache_tree.get_children())
        for i, line in enumerate(self.cpu.data_cache.lines):
            data_str = str([f"{x:04X}" for x in line.data])
            self.d_cache_tree.insert("", "end", values=(i, line.valid, line.tag, line.dirty, data_str))

        #Cache de instruções
        self.i_cache_tree.delete(*self.i_cache_tree.get_children())
        for i, line in enumerate(self.cpu.inst_cache.lines):
            data_str = str([f"{x:04X}" for x in line.data])
            self.i_cache_tree.insert("", "end", values=(i, line.valid, line.tag, line.dirty, data_str))

        #Logs do sistema (cache hit, cache miss e microinstruções)
        for log in self.cpu.data_cache.log:
            self.log(f"[D-CACHE] {log}")
        self.cpu.data_cache.log.clear()
        
        for log in self.cpu.inst_cache.log:
            self.log(f"[I-CACHE] {log}")
        self.cpu.inst_cache.log.clear()
        
        for micro in self.cpu.micro_log:
            self.log(f"[MICRO] {micro}")

    def log(self, msg):
        self.log_display.insert(tk.END, msg + "\n")
        self.log_display.see(tk.END)

    #Loop da thread de execução
    def run_loop(self):
        while self.running and not self.cpu.halted:
            self.cpu.step()
            # "after" é necessário porque Tkinter não é thread-safe
            self.root.after(0, self.update_ui)
            time.sleep(1.0 / self.speed_scale.get())
        
        self.running = False

    def start_simulation(self):
        if not self.running:
            self.running = True
            # Rodar em thread separada pra não travar a GUI
            threading.Thread(target=self.run_loop, daemon=True).start()

    def pause_simulation(self):
        self.running = False

    def step_simulation(self):
        self.pause_simulation()
        self.cpu.step()
        self.update_ui()

    def reset_simulation(self):
        self.pause_simulation()
        self.cpu.reset()
        self.log_display.delete("1.0", tk.END)
        self.update_full_memory_view()
        self.update_ui()

if __name__ == "__main__":
    root = tk.Tk()
    app = MIC1SimulatorApp(root)
    root.mainloop()