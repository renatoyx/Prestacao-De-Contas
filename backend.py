import os
import re
import sqlite3
import pandas as pd
import pdfplumber

DB_NAME = "financeiro.db"

def inicializar_banco():
    """Cria o banco de dados e as tabelas se não existirem."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

def extrair_despesas_pdf(caminho_pdf):
    texto_completo = ""
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for pagina in pdf.pages:
                texto_da_pagina = pagina.extract_text()
                if texto_da_pagina:
                    texto_completo += texto_da_pagina + "\n"
    except Exception as e:
        print(f"Erro ao ler o PDF: {e}")
        return []

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

def salvar_despesas_no_banco(caminho_pdf):
    despesas = extrair_despesas_pdf(caminho_pdf)
    if not despesas: return 0
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
    return novas_despesas

def obter_despesas_do_banco():
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT id, historico, data, valor FROM despesas ORDER BY data"
    cursor = conn.cursor()
    cursor.execute(query)
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def atualizar_despesa_no_banco(id_despesa, novo_historico, nova_data, novo_valor):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE despesas SET historico = ?, data = ?, valor = ? WHERE id = ?", (novo_historico, nova_data, novo_valor, id_despesa))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar despesa: {e}")
        return False

def exportar_para_xlsx(caminho_arquivo):
    """FUNÇÃO CORRIGIDA: Converte o valor para texto formatado antes de exportar."""
    try:
        conn = sqlite3.connect(DB_NAME)
        query = "SELECT historico AS 'Histórico', data AS 'Data', valor AS 'Valor (R$)' FROM despesas ORDER BY data"
        df = pd.read_sql_query(query, conn)
        conn.close()

        # --- NOVA LÓGICA DE FORMATAÇÃO ---
        # Converte a coluna de números para uma coluna de texto com a formatação desejada
        df['Valor (R$)'] = df['Valor (R$)'].apply(
            lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        )

        writer = pd.ExcelWriter(caminho_arquivo, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Despesas')

        workbook  = writer.book
        worksheet = writer.sheets['Despesas']

        # Apenas ajusta a largura da coluna, sem formato de número
        for i, col_nome in enumerate(df.columns):
            column_len = df[col_nome].astype(str).str.len().max()
            column_len = max(column_len, len(col_nome)) + 2
            worksheet.set_column(i, i, column_len)

        writer.close()
        return True
    except Exception as e:
        print(f"Erro ao exportar para XLSX: {e}")
        return False

def deletar_despesa_do_banco(id_despesa):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM despesas WHERE id = ?", (id_despesa,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao deletar despesa: {e}")
        return False

def resetar_banco_de_dados():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM despesas")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao resetar o banco de dados: {e}")
        return False