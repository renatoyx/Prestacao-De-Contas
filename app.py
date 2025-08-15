import os
import re
import sqlite3
import pandas as pd
import pdfplumber

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DB_NAME = "financeiro.db"

def inicializar_banco():
    """Cria o banco de dados e as tabelas se não existirem."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # A estrutura da tabela 'despesas' já prevê a associação futura com uma nota fiscal
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            historico TEXT NOT NULL,
            valor REAL NOT NULL,
            hash_transacao TEXT UNIQUE NOT NULL,
            id_nota_fiscal INTEGER
        )
    ''')
    
    # A tabela de notas fiscais será usada no futuro
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notas_fiscais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chave_nfe TEXT UNIQUE NOT NULL,
            razao_social TEXT,
            cnpj_cpf TEXT,
            data_emissao TEXT,
            numero_doc TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# --- MÓDULO DE PROCESSAMENTO DO EXTRATO ---
def extrair_transacoes_do_pdf(caminho_pdf):
    """Lê o extrato PDF e extrai apenas as transações de despesa (débito)."""
    texto_completo = ""
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto_da_pagina = pagina.extract_text()
            if texto_da_pagina:
                texto_completo += texto_da_pagina + "\n"

    transacoes = []
    padrao_transacao = re.compile(r'(\d{2}/\d{2}/\d{2,4})\s+(.*?)\s+([\d\.,]+-?)(?:\s+[\d\.,]+)?\s*$')

    for linha in texto_completo.split('\n'):
        match = padrao_transacao.search(linha)
        if match:
            data, descricao, valor_str = match.groups()
            descricao = re.sub(r'^\d+\s+', '', descricao).strip()
            descricao = re.sub(r'\s{2,}', ' ', descricao)
            
            try:
                if valor_str.endswith('-'):
                    valor_limpo = valor_str.replace('.', '').replace(',', '.').replace('-', '')
                    valor_float = float(valor_limpo)
                    hash_transacao = f"{data}-{descricao[:50]}-{valor_float}"

                    transacoes.append({
                        'data': data,
                        'historico': descricao,
                        'valor': valor_float,
                        'hash_transacao': hash_transacao
                    })
            except ValueError:
                continue
    
    return transacoes

# --- LÓGICA PRINCIPAL DO APP ---
def main():
    inicializar_banco()
    
    while True:
        print("\n--- Gestor Financeiro v0.5 ---")
        print("[1] Importar Despesas de um Extrato PDF")
        print("[2] Associar Nota Fiscal a uma Despesa (Em Breve)")
        print("[3] Ver Relatório de Despesas")
        print("[4] Sair")
        
        escolha = input("Escolha uma opção: ")

        if escolha == '1':
            arquivos_pdf = [f for f in os.listdir('extratos') if f.lower().endswith('.pdf')]
            if not arquivos_pdf:
                print("\nNenhum arquivo PDF encontrado na pasta 'extratos/'.")
                continue
            
            print("\nSelecione o extrato para importar:")
            for i, nome_arquivo in enumerate(arquivos_pdf):
                print(f"  [{i + 1}] - {nome_arquivo}")
            
            try:
                pdf_escolhido_idx = int(input("Digite o número do arquivo: ")) - 1
                if 0 <= pdf_escolhido_idx < len(arquivos_pdf):
                    caminho_pdf = os.path.join('extratos', arquivos_pdf[pdf_escolhido_idx])
                    despesas = extrair_transacoes_do_pdf(caminho_pdf)
                    
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    novas_despesas = 0
                    for d in despesas:
                        try:
                            cursor.execute(
                                "INSERT INTO despesas (data, historico, valor, hash_transacao) VALUES (?, ?, ?, ?)",
                                (d['data'], d['historico'], d['valor'], d['hash_transacao'])
                            )
                            novas_despesas += 1
                        except sqlite3.IntegrityError:
                            pass
                    conn.commit()
                    conn.close()
                    print(f"\nImportação concluída! {novas_despesas} novas despesas salvas.")
            except (ValueError, IndexError):
                print("\nOpção inválida.")

        elif escolha == '2':
            print("\n>> Funcionalidade em desenvolvimento. Em breve você poderá associar notas fiscais aqui! <<")

        elif escolha == '3':
            conn = sqlite3.connect(DB_NAME)
            query = "SELECT data, historico, valor FROM despesas ORDER BY data"
            df_relatorio = pd.read_sql_query(query, conn)
            
            if df_relatorio.empty:
                print("\nNenhum dado para mostrar. Importe um extrato na opção [1].")
            else:
                df_relatorio['valor'] = df_relatorio['valor'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                print("\n--- Relatório de Despesas ---")
                print(df_relatorio.to_string())
            
            conn.close()

        elif escolha == '4':
            print("Saindo do programa. Até mais!")
            break
        
        else:
            print("\nOpção inválida. Tente novamente.")

if __name__ == "__main__":
    main()