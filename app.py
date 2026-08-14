"""
Sistema de Controle de Almoxarifado - Secretaria de Saúde
Equipamentos por Unidade + Insumos Centralizados
Stack: Flask + SQLite + HTML/CSS/JS
"""

from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'chave_secreta_alterar_em_producao'

# Configuraç¬¬o do banco de dados
DATABASE = 'almoxarifado.db'

def get_db_connection():
    """Retorna conexa~o com o banco SQLite"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # permite acessar colunas por nome
    return conn

def init_db():
    """Inicializa o banco de dados com o schema"""
    conn = get_db_connection()
    with open('schema_almoxarifado.sql', 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

# ==================== ROTAS ====================

@app.route('/')
def index():
    """Pa'gina inicial do sistema"""
    return render_template('index.html')

@app.route('/unidades')
def unidades():
    """Lista todas as unidades de saude"""
    conn = get_db_connection()
    unidades = conn.execute('SELECT * FROM unidades ORDER BY nome').fetchall()
    conn.close()
    return render_template('unidades.html', unidades=unidades)

@app.route('/equipamentos')
def equipamentos():
    """Lista todos os equipamentos com unidade"""
    conn = get_db_connection()
    equipamentos = conn.execute('''
        SELECT e.*, u.nome as nome_unidade 
        FROM equipamentos e
        JOIN unidades u ON e.id_unidade = u.id_unidade
        ORDER BY u.nome, e.patrimonio
    ''').fetchall()
    conn.close()
    return render_template('equipamentos.html', equipamentos=equipamentos)

@app.route('/insumos')
def insumos():
    """Lista todos os insumos (almoxarifado + unidades)"""
    conn = get_db_connection()
    insumos = conn.execute('''
        SELECT i.*, u.nome as nome_unidade 
        FROM insumos i
        LEFT JOIN unidades u ON i.id_unidade = u.id_unidade
        ORDER BY i.vencimento, i.modelo
    ''').fetchall()
    conn.close()
    return render_template('insumos.html', insumos=insumos)

# ==================== INICIALIZAÇ¬O ====================

if __name__ == '__main__':
    # Inicializa o banco na primeira execuç¬¬o
    init_db()
    # Roda o servidor em modo desenvolvimento
    app.run(debug=True)
