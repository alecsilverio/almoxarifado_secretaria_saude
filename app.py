"""
Sistema de Controle de Almoxarifado - Secretaria de Saúde
Equipamentos por Unidade + Insumos Centralizados
Stack: Flask + SQLite + HTML/CSS/JS
"""

import os
import sqlite3
import csv

from io import StringIO
from datetime import timedelta, datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


# =========================================================
# CONFIGURAÇÕES
# =========================================================

# Usuário e senha do administrador.
# Em produção, defina ADMIN_USER e ADMIN_PASS como variáveis de ambiente.
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin")

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "almoxarifado.db"
SCHEMA = BASE_DIR / "schema_almoxarifado.sql"

app = Flask(__name__)

# Em produção, defina uma SECRET_KEY segura por variável de ambiente.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "chave-apenas-para-desenvolvimento-local"
)

# Mantém a sessão ativa por até 8 horas.
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)


# =========================================================
# AUTENTICAÇÃO
# =========================================================

def login_required(f):
    """Decorator para exigir login nas rotas administrativas."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Você precisa fazer login para acessar esta página.", "erro")
            return redirect(url_for("login", next=request.url))

        return f(*args, **kwargs)

    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    """Tela de login do administrador."""

    # Se já estiver logado, não precisa voltar à tela de login.
    if session.get("logged_in"):
        return redirect(url_for("index"))

    erro = None

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")

        if not usuario or not senha:
            erro = "Informe o usuário e a senha."

        elif usuario == ADMIN_USER and senha == ADMIN_PASS:
            # Limpa uma sessão antiga antes de criar uma nova.
            session.clear()

            session["logged_in"] = True
            session["usuario"] = usuario
            session.permanent = True

            flash("Login realizado com sucesso!", "sucesso")

            # Retorna para a página que a pessoa tentou abrir antes do login.
            proxima_pagina = request.args.get("next")

            # Aceita somente caminhos internos para evitar redirecionamento externo.
            if proxima_pagina and proxima_pagina.startswith("/"):
                return redirect(proxima_pagina)

            return redirect(url_for("index"))

        else:
            erro = "Usuário ou senha inválidos."

    return render_template("login.html", erro=erro)


@app.route("/logout")
@login_required
def logout():
    """Realiza logout do administrador."""

    session.clear()
    flash("Logout realizado com sucesso!", "sucesso")

    return redirect(url_for("login"))


# =========================================================
# BANCO DE DADOS
# =========================================================

def get_db_connection():
    """Retorna uma conexão com o banco SQLite."""

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    # Faz o SQLite respeitar as chaves estrangeiras.
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_db():
    """Cria as tabelas do banco, caso ainda não existam."""

    if not SCHEMA.exists():
        raise FileNotFoundError(
            f"Arquivo de esquema não encontrado: {SCHEMA.name}"
        )

    with get_db_connection() as conn:
        with open(SCHEMA, "r", encoding="utf-8") as arquivo:
            conn.executescript(arquivo.read())

def gerar_csv(nome_arquivo, cabecalhos, linhas):
    """
    Gera um arquivo CSV para download.
    Usa ; como separador, compatível com Excel em português.
    """

    arquivo = StringIO()
    writer = csv.writer(arquivo, delimiter=";")

    writer.writerow(cabecalhos)

    for linha in linhas:
        writer.writerow(linha)

    resposta = Response(
        arquivo.getvalue(),
        mimetype="text/csv; charset=utf-8"
    )

    resposta.headers["Content-Disposition"] = (
        f'attachment; filename="{nome_arquivo}"'
    )

    return resposta


def status_vencimento(vencimento):
    """Retorna o status do vencimento para exibição no relatório."""

    if not vencimento:
        return "Sem data de vencimento"

    try:
        data_vencimento = datetime.strptime(
            vencimento,
            "%Y-%m-%d"
        ).date()

        hoje = datetime.now().date()
        dias_restantes = (data_vencimento - hoje).days

        if dias_restantes < 0:
            return "Vencido"

        if dias_restantes <= 30:
            return "Próximo do vencimento"

        return "Válido"

    except ValueError:
        return "Data inválida"


# =========================================================
# PÁGINA INICIAL
# =========================================================

@app.route("/")
@login_required
def index():
    """Página inicial do sistema."""

    with get_db_connection() as conn:
        total_unidades = conn.execute(
            "SELECT COUNT(*) AS total FROM unidades"
        ).fetchone()["total"]

        total_equipamentos = conn.execute(
            "SELECT COUNT(*) AS total FROM equipamentos"
        ).fetchone()["total"]

        total_insumos = conn.execute(
            "SELECT COUNT(*) AS total FROM insumos"
        ).fetchone()["total"]

        total_vencidos = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM insumos
            WHERE vencimento IS NOT NULL
            AND date(vencimento) < date('now')
            """
        ).fetchone()["total"]

        total_proximos_vencimento = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM insumos
            WHERE vencimento IS NOT NULL
            AND date(vencimento) >= date('now')
            AND date(vencimento) <= date('now', '+30 days')
            """
        ).fetchone()["total"]

    return render_template(
        "index.html",
        total_unidades=total_unidades,
        total_equipamentos=total_equipamentos,
        total_insumos=total_insumos,
        total_vencidos=total_vencidos,
        total_proximos_vencimento=total_proximos_vencimento,
    )


# =========================================================
# UNIDADES
# =========================================================

@app.route("/unidades", methods=["GET", "POST"])
@login_required
def unidades():
    """Lista e cadastra unidades de saúde."""

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip().upper()
        nome = request.form.get("nome", "").strip()
        tipo = request.form.get("tipo", "").strip()
        endereco = request.form.get("endereco", "").strip()

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
                flash(
                    "Já existe uma unidade cadastrada com este código.",
                    "erro"
                )

    termo_busca = request.args.get("busca", "").strip()

    with get_db_connection() as conn:
        if termo_busca:
            lista_unidades = conn.execute(
                """
                SELECT *
                FROM unidades
                WHERE codigo LIKE ?
                OR nome LIKE ?
                OR tipo LIKE ?
                ORDER BY nome
                """,
                (
                    f"%{termo_busca}%",
                    f"%{termo_busca}%",
                    f"%{termo_busca}%",
                ),
            ).fetchall()
        else:
            lista_unidades = conn.execute(
                "SELECT * FROM unidades ORDER BY nome"
            ).fetchall()

    return render_template(
        "unidades.html",
        unidades=lista_unidades,
        busca=termo_busca,
    )


# =========================================================
# EQUIPAMENTOS
# =========================================================

@app.route("/equipamentos", methods=["GET", "POST"])
@login_required
def equipamentos():
    """Lista e cadastra equipamentos vinculados às unidades."""

    if request.method == "POST":
        id_unidade_texto = request.form.get("id_unidade", "").strip()
        patrimonio = request.form.get("patrimonio", "").strip().upper()
        nome = request.form.get("nome", "").strip()
        modelo = request.form.get("modelo", "").strip()
        marca = request.form.get("marca", "").strip()
        numero_serie = request.form.get("numero_serie", "").strip()
        data_entrada = request.form.get("data_entrada", "").strip() or None
        situacao = request.form.get("situacao", "").strip()
        observacao = request.form.get("observacao", "").strip()

        try:
            id_unidade = int(id_unidade_texto)
        except ValueError:
            id_unidade = None

        if not id_unidade or not patrimonio or not nome or not situacao:
            flash(
                "Unidade, patrimônio, nome e situação são obrigatórios.",
                "erro"
            )

        else:
            try:
                with get_db_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO equipamentos
                        (
                            id_unidade,
                            patrimonio,
                            nome,
                            modelo,
                            marca,
                            numero_serie,
                            data_entrada,
                            situacao,
                            observacao
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            id_unidade,
                            patrimonio,
                            nome,
                            modelo,
                            marca,
                            numero_serie,
                            data_entrada,
                            situacao,
                            observacao,
                        ),
                    )

                flash("Equipamento cadastrado com sucesso!", "sucesso")
                return redirect(url_for("equipamentos"))

            except sqlite3.IntegrityError:
                flash(
                    "Já existe um equipamento com este patrimônio nesta unidade.",
                    "erro"
                )

    busca = request.args.get("busca", "").strip()
    filtro_unidade = request.args.get("id_unidade", "").strip()
    filtro_situacao = request.args.get("situacao", "").strip()

    consulta = """
        SELECT
            e.*,
            u.nome AS nome_unidade,
            u.codigo AS codigo_unidade
        FROM equipamentos e
        JOIN unidades u ON e.id_unidade = u.id_unidade
        WHERE 1 = 1
    """

    parametros = []

    if busca:
        consulta += """
            AND (
                e.patrimonio LIKE ?
                OR e.nome LIKE ?
                OR e.modelo LIKE ?
                OR e.marca LIKE ?
                OR e.numero_serie LIKE ?
                OR u.nome LIKE ?
            )
        """

        termo = f"%{busca}%"
        parametros.extend([termo, termo, termo, termo, termo, termo])

    if filtro_unidade:
        try:
            consulta += " AND e.id_unidade = ?"
            parametros.append(int(filtro_unidade))
        except ValueError:
            pass

    if filtro_situacao:
        consulta += " AND e.situacao = ?"
        parametros.append(filtro_situacao)

    consulta += " ORDER BY u.nome, e.patrimonio, e.nome"

    with get_db_connection() as conn:
        lista_equipamentos = conn.execute(
            consulta,
            parametros,
        ).fetchall()

        lista_unidades = conn.execute(
            """
            SELECT id_unidade, codigo, nome
            FROM unidades
            ORDER BY nome
            """
        ).fetchall()

    return render_template(
        "equipamentos.html",
        equipamentos=lista_equipamentos,
        unidades=lista_unidades,
        busca=busca,
        filtro_unidade=filtro_unidade,
        filtro_situacao=filtro_situacao,
    )


# =========================================================
# INSUMOS
# =========================================================

@app.route("/insumos", methods=["GET", "POST"])
@login_required
def insumos():
    """Lista e cadastra insumos do almoxarifado e das unidades."""

    if request.method == "POST":
        id_unidade_texto = request.form.get("id_unidade", "").strip()

        if id_unidade_texto:
            try:
                id_unidade = int(id_unidade_texto)
            except ValueError:
                id_unidade = None
        else:
            # None representa material armazenado no almoxarifado central.
            id_unidade = None

        modelo = request.form.get("modelo", "").strip()
        marca = request.form.get("marca", "").strip()
        numero_serie = request.form.get("numero_serie", "").strip()

        quantidade_texto = request.form.get("quantidade", "0").strip()

        try:
            quantidade = int(quantidade_texto)
        except ValueError:
            quantidade = -1

        data_entrega = request.form.get(
            "data_entrega",
            ""
        ).strip() or None

        data_fabricacao = request.form.get(
            "data_fabricacao",
            ""
        ).strip() or None

        vencimento = request.form.get(
            "vencimento",
            ""
        ).strip() or None

        localizacao = request.form.get("localizacao", "").strip()
        observacao = request.form.get("observacao", "").strip()

        if not modelo or not marca:
            flash("Modelo e marca são obrigatórios.", "erro")

        elif quantidade < 0:
            flash(
                "A quantidade deve ser um número inteiro igual ou maior que zero.",
                "erro"
            )

        else:
            try:
                with get_db_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO insumos
                        (
                            id_unidade,
                            modelo,
                            marca,
                            numero_serie,
                            quantidade,
                            data_entrega,
                            data_fabricacao,
                            vencimento,
                            localizacao,
                            observacao
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            id_unidade,
                            modelo,
                            marca,
                            numero_serie,
                            quantidade,
                            data_entrega,
                            data_fabricacao,
                            vencimento,
                            localizacao,
                            observacao,
                        ),
                    )

                flash("Insumo cadastrado com sucesso!", "sucesso")
                return redirect(url_for("insumos"))

            except sqlite3.IntegrityError:
                flash(
                    "Não foi possível cadastrar o insumo. "
                    "Verifique os dados informados.",
                    "erro"
                )

            except sqlite3.Error as erro_banco:
                flash(
                    f"Erro ao cadastrar insumo: {erro_banco}",
                    "erro"
                )

    busca = request.args.get("busca", "").strip()
    filtro_unidade = request.args.get("id_unidade", "").strip()
    filtro_vencimento = request.args.get("vencimento", "").strip()

    consulta = """
        SELECT
            i.*,
            u.nome AS nome_unidade,
            u.codigo AS codigo_unidade,
            CASE
                WHEN i.vencimento IS NULL OR i.vencimento = '' THEN 'sem_vencimento'
                WHEN date(i.vencimento) < date('now') THEN 'vencido'
                WHEN date(i.vencimento) <= date('now', '+30 days') THEN 'proximo_vencimento'
                ELSE 'valido'
            END AS status_vencimento
        FROM insumos i
        LEFT JOIN unidades u ON i.id_unidade = u.id_unidade
        WHERE 1 = 1
    """

    parametros = []

    if busca:
        consulta += """
            AND (
                i.modelo LIKE ?
                OR i.marca LIKE ?
                OR i.numero_serie LIKE ?
                OR i.localizacao LIKE ?
                OR u.nome LIKE ?
            )
        """

        termo = f"%{busca}%"
        parametros.extend([termo, termo, termo, termo, termo])

    if filtro_unidade == "almoxarifado":
        consulta += " AND i.id_unidade IS NULL"

    elif filtro_unidade:
        try:
            consulta += " AND i.id_unidade = ?"
            parametros.append(int(filtro_unidade))
        except ValueError:
            pass

    if filtro_vencimento == "vencido":
        consulta += """
            AND i.vencimento IS NOT NULL
            AND i.vencimento <> ''
            AND date(i.vencimento) < date('now')
        """

    elif filtro_vencimento == "proximo":
        consulta += """
            AND i.vencimento IS NOT NULL
            AND i.vencimento <> ''
            AND date(i.vencimento) >= date('now')
            AND date(i.vencimento) <= date('now', '+30 days')
        """

    elif filtro_vencimento == "valido":
        consulta += """
            AND (
                i.vencimento IS NULL
                OR i.vencimento = ''
                OR date(i.vencimento) > date('now', '+30 days')
            )
        """

    consulta += """
        ORDER BY
            CASE
                WHEN i.vencimento IS NULL OR i.vencimento = '' THEN 2
                ELSE 1
            END,
            date(i.vencimento),
            i.modelo,
            i.marca
    """

    with get_db_connection() as conn:
        lista_insumos = conn.execute(
            consulta,
            parametros,
        ).fetchall()

        lista_unidades = conn.execute(
            """
            SELECT id_unidade, codigo, nome
            FROM unidades
            ORDER BY nome
            """
        ).fetchall()

    return render_template(
        "insumos.html",
        insumos=lista_insumos,
        unidades=lista_unidades,
        busca=busca,
        filtro_unidade=filtro_unidade,
        filtro_vencimento=filtro_vencimento,
    )


# =========================================================
# EXECUÇÃO LOCAL
# =========================================================

@app.route("/relatorios")
@login_required
def relatorios():
    """Exibe os relatórios gerais do sistema."""

    with get_db_connection() as conn:
        relatorio_unidades = conn.execute(
            """
            SELECT
                u.id_unidade,
                u.codigo,
                u.nome,
                u.tipo,
                u.endereco,
                COUNT(DISTINCT e.id_equipamento) AS total_equipamentos,
                COUNT(DISTINCT i.id_insumo) AS total_insumos
            FROM unidades u
            LEFT JOIN equipamentos e
                ON e.id_unidade = u.id_unidade
            LEFT JOIN insumos i
                ON i.id_unidade = u.id_unidade
            GROUP BY
                u.id_unidade,
                u.codigo,
                u.nome,
                u.tipo,
                u.endereco
            ORDER BY u.nome
            """
        ).fetchall()

        relatorio_equipamentos = conn.execute(
            """
            SELECT
                e.id_equipamento,
                u.codigo AS codigo_unidade,
                u.nome AS nome_unidade,
                e.patrimonio,
                e.nome,
                e.modelo,
                e.marca,
                e.numero_serie,
                e.data_entrada,
                e.situacao,
                e.observacao
            FROM equipamentos e
            JOIN unidades u
                ON e.id_unidade = u.id_unidade
            ORDER BY
                u.nome,
                e.nome,
                e.patrimonio
            """
        ).fetchall()

        relatorio_insumos = conn.execute(
            """
            SELECT
                i.id_insumo,
                COALESCE(u.codigo, 'ALMOXARIFADO') AS codigo_unidade,
                COALESCE(u.nome, 'Almoxarifado Central') AS nome_unidade,
                i.modelo,
                i.marca,
                i.numero_serie,
                i.quantidade,
                i.data_entrega,
                i.data_fabricacao,
                i.vencimento,
                i.localizacao,
                i.observacao,
                CASE
                    WHEN i.vencimento IS NULL OR i.vencimento = ''
                        THEN 'Sem data de vencimento'
                    WHEN date(i.vencimento) < date('now')
                        THEN 'Vencido'
                    WHEN date(i.vencimento) <= date('now', '+30 days')
                        THEN 'Próximo do vencimento'
                    ELSE 'Válido'
                END AS status_vencimento
            FROM insumos i
            LEFT JOIN unidades u
                ON i.id_unidade = u.id_unidade
            ORDER BY
                CASE
                    WHEN i.vencimento IS NULL OR i.vencimento = ''
                        THEN 2
                    ELSE 1
                END,
                date(i.vencimento),
                i.modelo,
                i.marca
            """
        ).fetchall()

        resumo = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM unidades) AS total_unidades,
                (SELECT COUNT(*) FROM equipamentos) AS total_equipamentos,
                (SELECT COUNT(*) FROM insumos) AS total_insumos,
                (
                    SELECT COUNT(*)
                    FROM insumos
                    WHERE vencimento IS NOT NULL
                    AND vencimento <> ''
                    AND date(vencimento) < date('now')
                ) AS total_vencidos,
                (
                    SELECT COUNT(*)
                    FROM insumos
                    WHERE vencimento IS NOT NULL
                    AND vencimento <> ''
                    AND date(vencimento) >= date('now')
                    AND date(vencimento) <= date('now', '+30 days')
                ) AS total_proximos_vencimento
            """
        ).fetchone()

    return render_template(
        "relatorios.html",
        resumo=resumo,
        relatorio_unidades=relatorio_unidades,
        relatorio_equipamentos=relatorio_equipamentos,
        relatorio_insumos=relatorio_insumos,
    )

@app.route("/relatorios/unidades/csv")
@login_required
def relatorio_unidades_csv():
    """Exporta o relatório de unidades em CSV."""

    with get_db_connection() as conn:
        unidades = conn.execute(
            """
            SELECT
                u.codigo,
                u.nome,
                u.tipo,
                u.endereco,
                COUNT(DISTINCT e.id_equipamento) AS total_equipamentos,
                COUNT(DISTINCT i.id_insumo) AS total_insumos
            FROM unidades u
            LEFT JOIN equipamentos e
                ON e.id_unidade = u.id_unidade
            LEFT JOIN insumos i
                ON i.id_unidade = u.id_unidade
            GROUP BY
                u.id_unidade,
                u.codigo,
                u.nome,
                u.tipo,
                u.endereco
            ORDER BY u.nome
            """
        ).fetchall()

    cabecalhos = [
        "Código",
        "Nome da unidade",
        "Tipo",
        "Endereço",
        "Total de equipamentos",
        "Total de insumos",
    ]

    linhas = [
        [
            unidade["codigo"],
            unidade["nome"],
            unidade["tipo"],
            unidade["endereco"],
            unidade["total_equipamentos"],
            unidade["total_insumos"],
        ]
        for unidade in unidades
    ]

    return gerar_csv(
        "relatorio_unidades.csv",
        cabecalhos,
        linhas,
    )


@app.route("/relatorios/equipamentos/csv")
@login_required
def relatorio_equipamentos_csv():
    """Exporta o relatório de equipamentos em CSV."""

    with get_db_connection() as conn:
        equipamentos = conn.execute(
            """
            SELECT
                u.codigo AS codigo_unidade,
                u.nome AS nome_unidade,
                e.patrimonio,
                e.nome,
                e.modelo,
                e.marca,
                e.numero_serie,
                e.data_entrada,
                e.situacao,
                e.observacao
            FROM equipamentos e
            JOIN unidades u
                ON e.id_unidade = u.id_unidade
            ORDER BY
                u.nome,
                e.nome,
                e.patrimonio
            """
        ).fetchall()

    cabecalhos = [
        "Código da unidade",
        "Unidade",
        "Patrimônio",
        "Equipamento",
        "Modelo",
        "Marca",
        "Número de série",
        "Data de entrada",
        "Situação",
        "Observação",
    ]

    linhas = [
        [
            equipamento["codigo_unidade"],
            equipamento["nome_unidade"],
            equipamento["patrimonio"],
            equipamento["nome"],
            equipamento["modelo"],
            equipamento["marca"],
            equipamento["numero_serie"],
            equipamento["data_entrada"],
            equipamento["situacao"],
            equipamento["observacao"],
        ]
        for equipamento in equipamentos
    ]

    return gerar_csv(
        "relatorio_equipamentos.csv",
        cabecalhos,
        linhas,
    )


@app.route("/relatorios/insumos/csv")
@login_required
def relatorio_insumos_csv():
    """Exporta o relatório de insumos em CSV."""

    with get_db_connection() as conn:
        insumos = conn.execute(
            """
            SELECT
                COALESCE(u.codigo, 'ALMOXARIFADO') AS codigo_unidade,
                COALESCE(u.nome, 'Almoxarifado Central') AS nome_unidade,
                i.modelo,
                i.marca,
                i.numero_serie,
                i.quantidade,
                i.data_entrega,
                i.data_fabricacao,
                i.vencimento,
                i.localizacao,
                i.observacao,
                CASE
                    WHEN i.vencimento IS NULL OR i.vencimento = ''
                        THEN 'Sem data de vencimento'
                    WHEN date(i.vencimento) < date('now')
                        THEN 'Vencido'
                    WHEN date(i.vencimento) <= date('now', '+30 days')
                        THEN 'Próximo do vencimento'
                    ELSE 'Válido'
                END AS status_vencimento
            FROM insumos i
            LEFT JOIN unidades u
                ON i.id_unidade = u.id_unidade
            ORDER BY
                CASE
                    WHEN i.vencimento IS NULL OR i.vencimento = ''
                        THEN 2
                    ELSE 1
                END,
                date(i.vencimento),
                i.modelo,
                i.marca
            """
        ).fetchall()

    cabecalhos = [
        "Código da unidade",
        "Unidade ou local",
        "Modelo",
        "Marca",
        "Lote / número de série",
        "Quantidade",
        "Data de entrega",
        "Data de fabricação",
        "Data de vencimento",
        "Localização",
        "Status de vencimento",
        "Observação",
    ]

    linhas = [
        [
            insumo["codigo_unidade"],
            insumo["nome_unidade"],
            insumo["modelo"],
            insumo["marca"],
            insumo["numero_serie"],
            insumo["quantidade"],
            insumo["data_entrega"],
            insumo["data_fabricacao"],
            insumo["vencimento"],
            insumo["localizacao"],
            insumo["status_vencimento"],
            insumo["observacao"],
        ]
        for insumo in insumos
    ]

    return gerar_csv(
        "relatorio_insumos.csv",
        cabecalhos,
        linhas,
    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True)