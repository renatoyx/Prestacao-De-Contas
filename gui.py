import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import backend
import re

# --- PALETA DE CORES E FONTES ---
COR_FUNDO = "#eaf2f8"
COR_FRAME = "#ffffff"
COR_CABECALHO = "#d4e6f1"
COR_TEXTO = "#2c3e50"
COR_BOTAO_DELETAR = "#e74c3c"
COR_LINHA_IMPAR = "#f9f9f9"
COR_TITULO = "#003366"

FONTE_NORMAL = ("Segoe UI", 10)
FONTE_TOTAL = ("Segoe UI", 11, "bold")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestor de Prestação de Contas")
        self.geometry("1000x700")
        self.configure(bg=COR_FUNDO)

        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TLabel", background=COR_FUNDO, foreground=COR_TEXTO, font=FONTE_NORMAL)
        style.configure("TButton", font=FONTE_NORMAL, padding=5)
        style.configure("Treeview", rowheight=25, font=FONTE_NORMAL, background=COR_FRAME, fieldbackground=COR_FRAME, foreground=COR_TEXTO)
        style.configure("Treeview.Heading", font=(FONTE_NORMAL[0], FONTE_NORMAL[1], 'bold'), background=COR_CABECALHO, relief="flat")
        style.configure("TLabelframe", background=COR_FUNDO)
        style.configure("TLabelframe.Label", font=FONTE_NORMAL, background=COR_FUNDO, foreground=COR_TITULO)
        style.configure("Delete.TButton", foreground="white", background=COR_BOTAO_DELETAR)
        style.map("Delete.TButton", background=[('active', '#c0392b')])

        self.criar_widgets()

        self.dados_originais = {}
        self.atualizar_tabela()

    def criar_widgets(self):
        main_frame = tk.Frame(self, bg=COR_FUNDO, padx=10, pady=10)
        main_frame.pack(expand=True, fill="both")

        frame_acoes = ttk.LabelFrame(main_frame, text=" Ações ")
        frame_acoes.pack(fill="x", pady=(0, 10))
        
        btn_importar = ttk.Button(frame_acoes, text="Importar Extrato", command=self.importar_extrato)
        btn_importar.pack(side="left", padx=5, pady=5)
        btn_salvar = ttk.Button(frame_acoes, text="Salvar Alterações", command=self.salvar_alteracoes)
        btn_salvar.pack(side="left", padx=5, pady=5)
        btn_exportar = ttk.Button(frame_acoes, text="Exportar para XLSX", command=self.exportar_xlsx)
        btn_exportar.pack(side="left", padx=5, pady=5)
        btn_deletar = ttk.Button(frame_acoes, text="Deletar Linha(s)", command=self.deletar_linha_selecionada, style="Delete.TButton")
        btn_deletar.pack(side="left", padx=5, pady=5)
        btn_resetar = ttk.Button(frame_acoes, text="Limpar Tudo", command=self.limpar_base_de_dados)
        btn_resetar.pack(side="left", padx=5, pady=5)

        frame_filtros = ttk.LabelFrame(main_frame, text=" Filtros e Visualização ")
        frame_filtros.pack(fill="x", pady=(0, 10))

        ttk.Label(frame_filtros, text="Buscar (Ctrl+F):").pack(side="left", padx=(5,0), pady=5)
        self.entry_busca = ttk.Entry(frame_filtros, font=FONTE_NORMAL)
        self.entry_busca.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.btn_limpar_busca = ttk.Button(frame_filtros, text="Limpar", command=self.limpar_filtro)
        self.btn_limpar_busca.pack(side="left", padx=(0, 15), pady=5)
        
        ttk.Label(frame_filtros, text="Exibir:").pack(side="left", pady=5)
        self.vars_colunas = {}
        for col in ["Histórico", "Data", "Valor"]:
            var = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(frame_filtros, text=col, variable=var, command=self.atualizar_colunas_visiveis, bg=COR_FUNDO, font=FONTE_NORMAL, activebackground=COR_FUNDO)
            cb.pack(side="left", padx=2, pady=5)
            self.vars_colunas[col] = var
        
        self.bind("<Control-f>", lambda event: self.entry_busca.focus_set())
        self.entry_busca.bind("<Return>", lambda event: self.filtrar_tabela())
        self.entry_busca.bind("<KeyRelease>", lambda event: self.filtrar_tabela())

        frame_tabela = tk.Frame(main_frame)
        frame_tabela.pack(expand=True, fill="both")
        
        scrollbar = ttk.Scrollbar(frame_tabela)
        scrollbar.pack(side="right", fill="y")
        
        self.colunas_id = ("id", "historico", "data", "valor")
        self.tabela = ttk.Treeview(frame_tabela, columns=[c for c in self.colunas_id if c != 'id'], show="headings", selectmode="extended", yscrollcommand=scrollbar.set)
        
        self.tabela.tag_configure('impar', background=COR_LINHA_IMPAR)
        self.tabela.tag_configure('par', background=COR_FRAME)
        
        scrollbar.config(command=self.tabela.yview)
        
        self.tabela.heading("historico", text="Histórico")
        self.tabela.heading("data", text="Data", anchor="center")
        self.tabela.heading("valor", text="Valor (R$)", anchor="e")
        self.tabela.column("historico", width=500)
        self.tabela.column("data", width=100, anchor="center")
        self.tabela.column("valor", width=120, anchor="e")
        
        self.tabela.pack(side="left", expand=True, fill="both")
        
        self.tabela.bind("<Double-1>", self.on_double_click)

        frame_totais = tk.Frame(main_frame, bg=COR_FUNDO)
        frame_totais.pack(fill="x", pady=(5,0), padx=5)
        
        self.label_total = tk.Label(frame_totais, text="Total Visível: R$ 0,00", font=FONTE_TOTAL, bg=COR_FUNDO, fg=COR_TITULO, anchor="e")
        self.label_total.pack(side="right")
    
    def preencher_tabela(self, dados):
        for i in self.tabela.get_children(): self.tabela.delete(i)
        
        soma_total = 0.0
        for i, item in enumerate(dados):
            tag = 'par' if i % 2 == 0 else 'impar'
            
            id_despesa, historico, data, valor = item
            self.tabela.insert("", "end", iid=id_despesa, values=(historico, data, f"{valor:,.2f}"), tags=(tag,))
            soma_total += valor
        
        self.label_total.config(text=f"Total Visível: R$ {soma_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

    def atualizar_tabela(self):
        dados = backend.obter_despesas_do_banco()
        self.dados_originais.clear()
        for item in dados:
            id_despesa, historico, data, valor = item
            self.dados_originais[id_despesa] = item
        self.preencher_tabela(list(self.dados_originais.values()))
        self.entry_busca.delete(0, tk.END)

    def filtrar_tabela(self, event=None):
        termo_busca = self.entry_busca.get().lower()
        if not termo_busca:
            self.preencher_tabela(list(self.dados_originais.values()))
            return
        
        dados_filtrados = []
        for item in self.dados_originais.values():
            historico_str = str(item[1]).lower()
            data_str = str(item[2]).lower()
            valor_str = f"{item[3]:,.2f}".replace('.', ',')
            
            if termo_busca in historico_str or termo_busca in data_str or termo_busca in valor_str:
                dados_filtrados.append(item)
        
        self.preencher_tabela(dados_filtrados)

    def limpar_filtro(self):
        self.entry_busca.delete(0, tk.END)
        self.preencher_tabela(list(self.dados_originais.values()))

    def importar_extrato(self):
        caminho_arquivo = filedialog.askopenfilename(filetypes=(("Arquivos PDF", "*.pdf"),))
        if not caminho_arquivo: return
        novas = backend.salvar_despesas_no_banco(caminho_arquivo)
        messagebox.showinfo("Importação Concluída", f"{novas} novas despesas importadas.")
        self.atualizar_tabela()

    def on_double_click(self, event):
        region = self.tabela.identify_region(event.x, event.y)
        if region != "cell": return
        item_id = self.tabela.focus()
        coluna_idx = self.tabela.identify_column(event.x)
        coluna_num = int(coluna_idx.replace('#', '')) - 1
        x, y, width, height = self.tabela.bbox(item_id, coluna_idx)
        valor_atual = self.tabela.item(item_id, "values")[coluna_num]
        entry = ttk.Entry(self, font=FONTE_NORMAL)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, valor_atual)
        entry.focus()
        entry.bind("<FocusOut>", lambda e: e.widget.destroy())
        entry.bind("<Return>", lambda e: self.salvar_edicao_celula(entry, item_id, coluna_num))

    def salvar_edicao_celula(self, entry, item_id, coluna_num):
        novo_valor = entry.get()
        valores_atuais = list(self.tabela.item(item_id, "values"))
        valores_atuais[coluna_num] = novo_valor
        self.tabela.item(item_id, values=valores_atuais)
        entry.destroy()

    def salvar_alteracoes(self):
        alteracoes_feitas = 0
        for item_id_str in self.tabela.get_children():
            item_id = int(item_id_str)
            valores_tela = self.tabela.item(item_id, "values")
            historico_tela, data_tela, valor_str_tela = valores_tela
            _id, orig_hist, orig_data, orig_valor = self.dados_originais[item_id]
            # --- LINHA CORRIGIDA ---
            try:
                valor_tela_str_limpo = re.sub(r'[^\d,]', '', valor_str_tela).replace(',', '.')
                valor_tela = float(valor_tela_str_limpo)
            except (ValueError, IndexError):
                messagebox.showerror("Erro de Formato", f"O valor '{valor_str_tela}' na linha ID {item_id} não é um número válido.")
                continue
            if (historico_tela != orig_hist) or (data_tela != orig_data) or (abs(valor_tela - orig_valor) > 0.001):
                if backend.atualizar_despesa_no_banco(item_id, historico_tela, data_tela, valor_tela):
                    alteracoes_feitas += 1
        if alteracoes_feitas > 0:
            messagebox.showinfo("Sucesso", f"{alteracoes_feitas} alterações foram salvas no banco de dados.")
            self.atualizar_tabela()
        else:
            messagebox.showinfo("Nenhuma Alteração", "Nenhuma alteração foi detectada para salvar.")
            
    def atualizar_colunas_visiveis(self):
        colunas_id_visiveis = [self.colunas_id[i+1] for i, col_nome in enumerate(self.vars_colunas) if self.vars_colunas[col_nome].get()]
        self.tabela["displaycolumns"] = colunas_id_visiveis

    def exportar_xlsx(self):
        caminho_arquivo = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Arquivos Excel", "*.xlsx")], title="Salvar relatório como...")
        if not caminho_arquivo: return
        if backend.exportar_para_xlsx(caminho_arquivo):
            messagebox.showinfo("Exportação Concluída", f"Relatório salvo com sucesso em:\n{caminho_arquivo}")
        else:
            messagebox.showerror("Erro na Exportação", "Não foi possível salvar o arquivo.")

    def deletar_linha_selecionada(self):
        selecionados = self.tabela.selection()
        if not selecionados:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma ou mais linhas para deletar.")
            return
        msg = f"Você tem certeza que deseja deletar permanentemente as {len(selecionados)} linhas selecionadas?"
        if messagebox.askyesno("Confirmar Deleção", msg):
            for item_id in selecionados:
                backend.deletar_despesa_do_banco(int(item_id))
            self.atualizar_tabela()
            messagebox.showinfo("Sucesso", "As linhas selecionadas foram deletadas.")

    def limpar_base_de_dados(self):
        msg = "ATENÇÃO!\n\nVocê tem certeza que deseja apagar TODOS os dados salvos? Esta ação não pode ser desfeita."
        if messagebox.askyesno("Confirmar Limpeza Total", msg, icon='warning'):
            if backend.resetar_banco_de_dados():
                self.atualizar_tabela()
                messagebox.showinfo("Sucesso", "Todos os dados foram apagados. Você pode começar um novo relatório.")
            else:
                messagebox.showerror("Erro", "Ocorreu um erro ao tentar limpar o banco de dados.")

if __name__ == "__main__":
    backend.inicializar_banco()
    app = App()
    app.mainloop()