import pdfplumber
import re

class ExtratoParser:
    def extrair_despesas_pdf(self, caminho_pdf):
        """Lê um PDF e retorna uma lista de dicionários com as despesas."""
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

        for linha in texto_completo.split('\n'):
            match_data = padrao_data.search(linha)
            if not match_data: continue

            data = match_data.group(1)
            candidatos_debito = padrao_valores.findall(linha)
            if not candidatos_debito: continue

            valor_str = min(candidatos_debito, key=lambda v: float(v.replace('.','').replace(',','.').replace('-','')))

            descricao = linha.replace(data, '')
            todos_numeros = re.findall(r'[\d\.,]+-?', linha)
            for num in todos_numeros:
                if num != data: descricao = descricao.replace(num, '')
            descricao = re.sub(r'\s{2,}', ' ', descricao).strip()

            try:
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