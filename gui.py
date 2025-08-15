import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import backend

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestor de Prestação de Contas")
        self.geometry("950x600")

        frame_controles = tk.Frame(self)
        frame_controles.pack(pady=10, padx=10, fill="x")
        
        frame_botoes = tk.Frame(frame_controles)
        frame_botoes.pack(side="left")
        
        frame_colunas = tk.Frame(frame_controles)
        frame_colunas.pack(side="right")

        self.btn_importar = tk.Button(frame_botoes, text="Importar Extrato PDF", command=self.importar_extrato)
        self.btn_importar.pack(side="left", padx=(0, 5))

        self.btn_salvar = tk.Button(frame_botoes, text="Salvar Alterações", command=self.salvar_alteracoes)
        self.btn_salvar.pack(side="left", padx=5)
        
        self.btn_exportar = tk.Button(frame_botoes, text="Exportar para XLSX", command=self.exportar_xlsx)
        self.btn_exportar.pack(side="left", padx=5)

        self.btn_deletar = tk.Button(frame_botoes, text="Deletar Linha(s)", command=self.deletar_linha_selecionada, bg="#ffcccb")
        self.btn_deletar.pack(side="left", padx=5)

        self.btn_resetar = tk.Button(frame_botoes, text="Limpar Tudo (Novo)", command=self.limpar_base_de_dados, bg="#ffebcc")
        self.btn_resetar.pack(side="left", padx=5)

        tk.Label(frame_colunas, text="Exibir Colunas:").pack(side="left", padx=5)
        self.vars_colunas = {}
        for col in ["Histórico", "Data", "Valor"]:
            var = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(frame_colunas, text=col, variable=var, command=self.atualizar_colunas_visiveis)
            cb.pack(side="left")
            self.vars_colunas[col] = var

        self.colunas_id = ("id", "historico", "data", "valor")
        self.tabela = ttk.Treeview(self, columns=[c for c in self.colunas_id if c != 'id'], show="headings", selectmode="extended")
        
        self.tabela.heading("historico", text="Histórico")
        self.tabela.heading("data", text="Data")
        self.tabela.heading("valor", text="Valor (R$)")
        self.tabela.column("historico", width=400)
        self.tabela.column("data", width=100)
        self.tabela.column("valor", width=100, anchor="e")
        self.tabela.pack(pady=10, padx=10, expand=True, fill="both")
        
        self.tabela.bind("<Double-1>", self.on_double_click)
        self.dados_originais = {}

        self.atualizar_tabela()

    def importar_extrato(self):
        caminho_arquivo = filedialog.askopenfilename(filetypes=(("Arquivos PDF", "*.pdf"),))
        if not caminho_arquivo: return
        novas = backend.salvar_despesas_no_banco(caminho_arquivo)
        messagebox.showinfo("Importação Concluída", f"{novas} novas despesas importadas.")
        self.atualizar_tabela()

    def atualizar_tabela(self):
        for i in self.tabela.get_children(): self.tabela.delete(i)
        dados = backend.obter_despesas_do_banco()
        self.dados_originais.clear()
        for item in dados:
            id_despesa, historico, data, valor = item
            self.tabela.insert("", "end", iid=id_despesa, values=(historico, data, f"{valor:,.2f}"))
            self.dados_originais[str(id_despesa)] = (historico, data, valor)

    def on_double_click(self, event):
        region = self.tabela.identify_region(event.x, event.y)
        if region != "cell": return
        item_id = self.tabela.focus()
        coluna_idx = self.tabela.identify_column(event.x)
        coluna_num = int(coluna_idx.replace('#', '')) - 1
        x, y, width, height = self.tabela.bbox(item_id, coluna_idx)
        valor_atual = self.tabela.item(item_id, "values")[coluna_num]
        entry = ttk.Entry(self)
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
        for item_id in self.tabela.get_children():
            valores_tela = self.tabela.item(item_id, "values")
            historico_tela, data_tela, valor_str_tela = valores_tela
            orig_hist, orig_data, orig_valor = self.dados_originais[item_id]
            try:
                valor_tela = float(valor_str_tela.replace('R$', '').replace('.', '').replace(',', '.'))
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
                backend.deletar_despesa_do_banco(item_id)
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