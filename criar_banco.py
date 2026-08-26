"""Script para criar o banco de dados do zero."""

from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "almoxarifado.db"
SCHEMA = BASE_DIR / "schema_almoxarifado.sql"

print(f"Banco: {DATABASE}")
print(f"Schema: {SCHEMA}")

if not SCHEMA.exists():
    print("ERRO: arquivo schema_almoxarifado.sql não encontrado!")
    exit(1)

with sqlite3.connect(DATABASE) as conn:
    with open(SCHEMA, "r", encoding="utf-8") as arquivo:
        conn.executescript(arquivo.read())

print("Banco criado com sucesso!")
print(f"Arquivo: {DATABASE}")