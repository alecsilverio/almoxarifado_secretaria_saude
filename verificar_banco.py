"""Verifica se as tabelas foram criadas no banco."""

import sqlite3

conn = sqlite3.connect("almoxarifado.db")
tabelas = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("Tabelas no banco:")
for t in tabelas:
    print("-", t[0])

conn.close()