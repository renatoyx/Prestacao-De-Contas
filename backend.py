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
            hash_transacao TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def extrair_despesas_pdf(caminho_pdf):
    """Lê um PDF e retorna uma lista de dicionários com as despesas, usando uma lógica mais robusta."""
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
    padrao_data = re.compile(r'(\d{2}/\d{2}/\d{2,4})')
    padrao_valores = re.compile(r'[\d\.,]+-')
    
    # Adiciona um contador de linha para garantir a unicidade
    contador_linha = 0

    for linha in texto_completo.split('\n'):
        contador_linha += 1
        
        match_data = padrao_data.search(linha)
        if not match_data:
            continue

        data = match_data.group(1)
        candidatos_debito = padrao_valores.findall(linha)

        if not candidatos_debito:
            continue

        valor_str = ""
        if len(candidatos_debito) == 1:
            valor_str = candidatos_debito[0]
        else:
            # Se há múltiplos valores negativos, escolhe o de menor valor absoluto
            menor_valor = float('inf')
            valor_final = ""
            for c in candidatos_debito:
                try:
                    valor_num = float(c.replace('.', '').replace(',', '.').replace('-', ''))
                    if valor_num < menor_valor:
                        menor_valor = valor_num
                        valor_final = c
                except ValueError:
                    continue
            valor_str = valor_final
        
        if not valor_str:
            continue

        descricao = linha
        descricao = descricao.replace(data, '')
        todos_os_numeros = re.findall(r'[\d\.,]+-?', linha)
        for num in todos_os_numeros:
             if num != data:
                descricao = descricao.replace(num, '')
        descricao = re.sub(r'\s{2,}', ' ', descricao).strip()

        try:
            valor_limpo = valor_str.replace('.', '').replace(',', '.').replace('-', '')
            valor_float = float(valor_limpo)
            # --- HASH CORRIGIDO ---
            # Adiciona o contador de linha para garantir que o hash seja sempre único
            hash_transacao = f"{data}-{descricao[:50]}-{valor_float}-{contador_linha}"
            transacoes.append({
                'data': data,
                'historico': descricao,
                'valor': valor_float,
                'hash_transacao': hash_transacao
            })
        except ValueError:
            continue
            
    return transacoes

# O restante do arquivo backend.py continua o mesmo...

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
    query = """
        SELECT id, historico, data, valor 
        FROM despesas 
        ORDER BY 
            SUBSTR(data, 7, 4), -- Ano
            SUBSTR(data, 4, 2), -- Mês
            SUBSTR(data, 1, 2)  -- Dia
    """
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
    try:
        conn = sqlite3.connect(DB_NAME)
        query = """
            SELECT historico AS 'Histórico', data AS 'Data', valor AS 'Valor (R$)'
            FROM despesas 
            ORDER BY 
                SUBSTR(data, 7, 4), -- Ano
                SUBSTR(data, 4, 2), -- Mês
                SUBSTR(data, 1, 2)  -- Dia
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        df['Valor (R$)'] = df['Valor (R$)'].round(2)
        writer = pd.ExcelWriter(caminho_arquivo, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Despesas')
        workbook  = writer.book
        worksheet = writer.sheets['Despesas']
        formato_numero = workbook.add_format({'num_format': '#,##0.00'})

        for i, col_nome in enumerate(df.columns):
            column_len = df[col_nome].astype(str).str.len().max()
            column_len = max(column_len, len(col_nome)) + 2
            
            if col_nome == 'Valor (R$)':
                worksheet.set_column(i, i, column_len, formato_numero)
            else:
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