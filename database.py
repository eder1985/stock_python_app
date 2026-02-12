import sqlite3

def conectar():
    return sqlite3.connect("estoque_motos.db")

def criar_tabela():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pecas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_sku TEXT,
            descricao TEXT,
            marca TEXT,
            compatibilidade TEXT,
            quantidade INTEGER,
            caminho_imagem TEXT
        )
    """)
    conn.commit()
    conn.close()

criar_tabela()