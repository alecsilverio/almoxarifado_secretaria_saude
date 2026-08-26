"""
Sistema de Controle de Almoxarifado - Secretaria de Saúde
Equipamentos por Unidade + Insumos Centralizados
Stack: Flask + SQLite + HTML/CSS/JS
"""

from pathlib import Path
import sqlite3

from flask import Flask, flash, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "almoxarifado.db"
SCHEMA = BASE_DIR / "schema_almoxarifado.sql"

app = Flask(__name__)
app.secret_key = "chave_secreta_alterar_em_producao"


def get_db_connection():
    """Retorna conexão com o banco SQLite."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria as tabelas do banco, caso elas ainda não existam."""
    with get_db_connection() as conn:
        with open(SCHEMA, "r", encoding="utf-8") as arquivo:
            conn.executescript(arquivo.read())


@app.route("/")
def index():
    """Página inicial do sistema."""
    return render_template("index.html")


@app.route("/unidades", methods=["GET", "POST"])
def unidades():
    """Lista e cadastra unidades de saúde."""
    if request.method == "POST":
        codigo = request.form["codigo"].strip().upper()
        nome = request.form["nome"].strip()
        tipo = request.form["tipo"].strip()
        endereco = request.form["endereco"].strip()

        if not codigo or not nome:
            flash("Código e nome da unidade são obrigatórios.", "erro")
        else:
            try:
                with get_db_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO unidades (codigo, nome, tipo, endereco)
                        VALUES (?, ?, ?, ?)
                        """,
                        (codigo, nome, tipo, endereco),
                    )

                flash("Unidade cadastrada com sucesso!", "sucesso")
                return redirect(url_for("unidades"))

            except sqlite3.IntegrityError:
                flash("Já existe uma unidade cadastrada com este código.", "erro")

    with get_db_connection() as conn:
        lista_unidades = conn.execute(
            "SELECT * FROM unidades ORDER BY nome"
        ).fetchall()

    return render_template("unidades.html", unidades=lista_unidades)


@app.route("/equipamentos", methods=["GET", "POST"])
def equipamentos():
    """Lista e cadastra equipamentos vinculados às unidades."""
    if request.method == "POST":
        id_unidade = int(request.form["id_unidade"])
        patrimonio = request.form["patrimonio"].strip().upper()
        nome = request.form["nome"].strip()
        modelo = request.form["modelo"].strip()
        marca = request.form["marca"].strip()
        numero_serie = request.form["numero_serie"].strip()
        data_entrada = request.form["data_entrada"].strip() or None
        situacao = request.form["situacao"].strip()
        observacao = request.form["observacao"].strip()

        if not id_unidade or not patrimonio:
            flash("Unidade e patrimônio são obrigatórios.", "erro")
        else:
            try:
                with get_db_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO equipamentos
                        (id_unidade, patrimonio, nome, modelo, marca, numero_serie,
                         data_entrada, situacao, observacao)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (id_unidade, patrimonio, nome, modelo, marca, numero_serie,
                         data_entrada, situacao, observacao),
                    )

                flash("Equipamento cadastrado com sucesso!", "sucesso")
                return redirect(url_for("equipamentos"))

            except sqlite3.IntegrityError:
                flash("Já existe um equipamento com este patrimônio nesta unidade.", "erro")

    with get_db_connection() as conn:
        lista_equipamentos = conn.execute(
            """
            SELECT e.*, u.nome AS nome_unidade
            FROM equipamentos e
            JOIN unidades u ON e.id_unidade = u.id_unidade
            ORDER BY u.nome, e.patrimonio
            """
        ).fetchall()

        lista_unidades = conn.execute(
            "SELECT id_unidade, codigo, nome FROM unidades ORDER BY nome"
        ).fetchall()

    return render_template(
        "equipamentos.html",
        equipamentos=lista_equipamentos,
        unidades=lista_unidades
    )


@app.route("/insumos")
def insumos():
    """Lista insumos do almoxarifado e das unidades."""
    with get_db_connection() as conn:
        lista_insumos = conn.execute(
            """
            SELECT i.*, u.nome AS nome_unidade
            FROM insumos i
            LEFT JOIN unidades u ON i.id_unidade = u.id_unidade
            ORDER BY i.vencimento, i.modelo
            """
        ).fetchall()

    return render_template("insumos.html", insumos=lista_insumos)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)