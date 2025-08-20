import sqlite3

DB_NAME = "financeiro.db"

class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self._inicializar_banco()

    def _inicializar_banco(self):
        """Método privado para criar as tabelas se não existirem."""
        conn = sqlite3.connect(self.db_name)
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

    def salvar_despesas(self, lista_despesas):
        """Recebe uma lista de despesas e as salva no banco."""
        if not lista_despesas:
            return 0
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        novas_despesas = 0
        for d in lista_despesas:
            try:
                cursor.execute(
                    "INSERT INTO despesas (data, historico, valor, hash_transacao) VALUES (?, ?, ?, ?)",
                    (d['data'], d['historico'], d['valor'], d['hash_transacao'])
                )
                novas_despesas += 1
            except sqlite3.IntegrityError:
                pass  # Ignora despesas duplicadas
        conn.commit()
        conn.close()
        return novas_despesas

    def obter_despesas(self):
        """Busca todas as despesas e as ordena cronologicamente."""
        conn = sqlite3.connect(self.db_name)
        query = """
            SELECT id, historico, data, valor 
            FROM despesas 
            ORDER BY 
                SUBSTR(data, 7, 4), SUBSTR(data, 4, 2), SUBSTR(data, 1, 2)
        """
        cursor = conn.cursor()
        cursor.execute(query)
        resultados = cursor.fetchall()
        conn.close()
        return resultados

    def atualizar_despesa(self, id_despesa, novo_historico, nova_data, novo_valor):
        """Atualiza uma despesa específica."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("UPDATE despesas SET historico = ?, data = ?, valor = ? WHERE id = ?", (novo_historico, nova_data, novo_valor, id_despesa))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def deletar_despesa(self, id_despesa):
        """Deleta uma despesa específica."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM despesas WHERE id = ?", (id_despesa,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def resetar_banco(self):
        """Deleta TODAS as despesas da tabela."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM despesas")
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False