import pdfplumber
import pandas as pd
import re
import os

def extrair_transacoes_do_pdf(caminho_pdf):
    """
    Função principal que lê um PDF de extrato bancário, extrai as transações
    e retorna uma tabela (DataFrame) com os dados organizados.
    """
    if not os.path.exists(caminho_pdf):
        print(f"Erro: Arquivo não encontrado no caminho: {caminho_pdf}")
        return None

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
            data = match.group(1)
            descricao = match.group(2).strip()
            valor_str = match.group(3)

            descricao = re.sub(r'^\d+\s+', '', descricao)
            descricao = re.sub(r'\s{2,}', ' ', descricao)

            try:
                is_debit = valor_str.endswith('-')
                valor_limpo = valor_str.replace('.', '').replace(',', '.').replace('-', '')
                valor_float = float(valor_limpo)
                if is_debit:
                    valor_float = -valor_float
                
                transacoes.append({
                    'Data': data,
                    'Histórico': descricao,
                    'Valor (R$)': valor_float
                })
            except ValueError:
                pass
    
    df = pd.DataFrame(transacoes)
    return df

# --- Execução do Script ---
if __name__ == "__main__":
    arquivos_pdf = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]

    if not arquivos_pdf:
        print("❌ Nenhum arquivo PDF foi encontrado nesta pasta.")
    else:
        print("📄 Arquivos PDF encontrados na pasta:")
        for i, nome_arquivo in enumerate(arquivos_pdf):
            print(f"  [{i + 1}] - {nome_arquivo}")
        
        while True:
            try:
                escolha = int(input("\nDigite o número do arquivo que você quer processar: "))
                if 1 <= escolha <= len(arquivos_pdf):
                    nome_arquivo_pdf = arquivos_pdf[escolha - 1]
                    break
                else:
                    print("Opção inválida. Por favor, digite um número da lista.")
            except ValueError:
                print("Entrada inválida. Por favor, digite apenas o número.")

        print(f"\nProcessando o arquivo: '{nome_arquivo_pdf}'...")
        
        df_extrato = extrair_transacoes_do_pdf(nome_arquivo_pdf)

        if df_extrato is not None and not df_extrato.empty:
            df_saidas = df_extrato[df_extrato['Valor (R$)'] < 0].copy()
            
            df_saidas['Valor (R$)'] = df_saidas['Valor (R$)'].apply(
                lambda valor: f"R$ {abs(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            )
            
            # >>> AQUI A COLUNA É REORGANIZADA PARA A ORDEM SOLICITADA <<<
            df_saidas = df_saidas[['Histórico', 'Data', 'Valor (R$)']]

            print("✅ Transações de SAÍDA extraídas e formatadas com sucesso!")
            
            print("\nAmostra dos dados de saída:")
            print(df_saidas.head())

            nome_base_arquivo = os.path.splitext(nome_arquivo_pdf)[0]
            nome_arquivo_csv = f"{nome_base_arquivo}_apenas_saidas.csv"
            
            df_saidas.to_csv(nome_arquivo_csv, index=False, sep=';')
            
            print(f"\n✅ Relatório de saídas salvo com sucesso no arquivo: {nome_arquivo_csv}")
        else:
            print("❌ Nenhuma transação foi extraída. Verifique o PDF ou o código.")