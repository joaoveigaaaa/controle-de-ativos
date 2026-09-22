import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

def conectar():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "numero_de_serie"),
        charset="utf8mb4",
        connection_timeout=10,
    )

def testar_conexao():
    conexao = None
    cursor = None

    try:
        conexao = conectar()
        cursor = conexao.cursor()

        cursor.execute("SELECT DATABASE()")
        nome_banco = cursor.fetchone()[0]
        print(f"Conexão realizada! Banco: {nome_banco}")

        cursor.execute("SELECT COUNT(*) FROM ativo")
        quantidade = cursor.fetchone()[0]
        print(f"Tabela ativo encontrada. Equipamentos: {quantidade}")

    except mysql.connector.Error as erro:
        print(f"Erro ao conectar ou consultar: {erro}")

    finally:
        if cursor is not None:
            cursor.close()

        if conexao is not None:
            conexao.close()

if __name__ == "__main__":
    testar_conexao()