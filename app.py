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
from uuid import uuid4


from flask import (
    Flask,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from werkzeug.utils import secure_filename

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
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
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_OS_FOLDER = os.path.join(
    BASE_DIR,
    "uploads",
    "ordens_servico",
)

ALLOWED_OS_EXTENSIONS = {"pdf"}

app.config["UPLOAD_OS_FOLDER"] = UPLOAD_OS_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

os.makedirs(
    app.config["UPLOAD_OS_FOLDER"],
    exist_ok=True,
)

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

def administrador_principal_required(f):
    """Permite acesso apenas ao administrador principal."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Você precisa fazer login para acessar esta página.", "erro")
            return redirect(url_for("login"))

        if session.get("papel_usuario") != "administrador_principal":
            flash(
                "Somente o administrador principal pode gerenciar usuários.",
                "erro",
            )
            return redirect(url_for("index"))

        return f(*args, **kwargs)

    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    """Tela de login dos usuários do sistema."""

    if session.get("logged_in"):
        if session.get("primeiro_acesso"):
            return redirect(url_for("primeiro_acesso"))

        return redirect(url_for("index"))

    erro = None

    if request.method == "POST":
        email = request.form.get("usuario", "").strip().lower()
        senha = request.form.get("senha", "")

        if not email or not senha:
            erro = "Informe o e-mail institucional e a senha."

        else:
            with get_db_connection() as conn:
                usuario = conn.execute(
                    """
                    SELECT
                        id_usuario,
                        nome,
                        email,
                        senha_hash,
                        papel,
                        ativo,
                        primeiro_acesso
                    FROM usuarios
                    WHERE email = ?
                    """,
                    (email,),
                ).fetchone()

            if usuario is None:
                erro = "E-mail ou senha inválidos."

            elif not usuario["ativo"]:
                erro = (
                    "Este usuário está desativado. "
                    "Procure o administrador principal."
                )

            elif not check_password_hash(usuario["senha_hash"], senha):
                erro = "E-mail ou senha inválidos."

            else:
                session.clear()

                session["logged_in"] = True
                session["id_usuario"] = usuario["id_usuario"]
                session["nome_usuario"] = usuario["nome"]
                session["email_usuario"] = usuario["email"]
                session["papel_usuario"] = usuario["papel"]
                session["primeiro_acesso"] = bool(
                    usuario["primeiro_acesso"]
                )

                session.permanent = True

                if session["primeiro_acesso"]:
                    flash(
                        "Por segurança, crie uma nova senha para continuar.",
                        "aviso",
                    )

                    return redirect(url_for("primeiro_acesso"))

                flash(
                    f"Bem-vindo(a), {usuario['nome']}!",
                    "sucesso",
                )

                proxima_pagina = request.args.get("next")

                if (
                    proxima_pagina
                    and proxima_pagina.startswith("/")
                    and not proxima_pagina.startswith("//")
                ):
                    return redirect(proxima_pagina)

                return redirect(url_for("index"))

    return render_template(
        "login.html",
        erro=erro,
    )

def criar_usuarios_iniciais():
    
    """
    Cria os três usuários institucionais apenas se ainda não existirem.

    Troque as senhas temporárias antes de rodar em apresentação ou uso real.
    Cada pessoa deve trocar sua senha no primeiro acesso.
    """

    usuarios_iniciais = [
        {
            "nome": "Alexandre Silvério Damião dos Santos",
            "email": "alexandre.silverio@treslagoas.ms.gov.br",
            "senha": os.environ.get(
                "SENHA_INICIAL_ALEXANDRE",
                "Trocar@2026Alexandre"
            ),
            "papel": "administrador_principal",
        },
        {
            "nome": "Márcio Alan Martins",
            "email": "marcio.martins@treslagoas.ms.gov.br",
            "senha": os.environ.get(
                "SENHA_INICIAL_MARCIO",
                "Trocar@2026Marcio"
            ),
            "papel": "administrador",
        },
        {
            "nome": "Alessandra Bruski de Oliveira de Paula",
            "email": "alessandra.paula@treslagoas.ms.gov.br",
            "senha": os.environ.get(
                "SENHA_INICIAL_ALESSANDRA",
                "Trocar@2026Alessandra"
            ),
            "papel": "administrador",
        },
    ]

    with get_db_connection() as conn:
        for usuario in usuarios_iniciais:
            existe = conn.execute(
                """
                SELECT id_usuario
                FROM usuarios
                WHERE email = ?
                """,
                (usuario["email"],),
            ).fetchone()

            if existe is None:
                conn.execute(
                    """
                    INSERT INTO usuarios
                    (
                        nome,
                        email,
                        senha_hash,
                        papel,
                        ativo,
                        primeiro_acesso
                    )
                    VALUES (?, ?, ?, ?, 1, 1)
                    """,
                    (
                        usuario["nome"],
                        usuario["email"],
                        generate_password_hash(usuario["senha"]),
                        usuario["papel"],
                    ),
                )


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
        grupo_rede = request.form.get("grupo_rede", "").strip()
        tipo_unidade = request.form.get("tipo_unidade", "").strip()
        endereco = request.form.get("endereco", "").strip()

        if not codigo or not nome or not grupo_rede or not tipo_unidade:
            flash(
                "Código, nome, grupo da rede e tipo de unidade são obrigatórios.",
                "erro"
            )
        else:
            try:
                with get_db_connection() as conn:
                    conn.execute("""
                        INSERT INTO unidades (
                            codigo,
                            nome,
                            grupo_rede,
                            tipo_unidade,
                            endereco
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        codigo,
                        nome,
                        grupo_rede,
                        tipo_unidade,
                        endereco
                    ))

                flash("Unidade cadastrada com sucesso!", "sucesso")
                return redirect(url_for("unidades"))

            except sqlite3.IntegrityError:
                flash(
                    "Já existe uma unidade cadastrada com este código.",
                    "erro"
                )

            except sqlite3.Error as erro_banco:
                flash(
                    f"Erro ao cadastrar a unidade: {erro_banco}",
                    "erro"
                )

    termo_busca = request.args.get("busca", "").strip()

    with get_db_connection() as conn:
        if termo_busca:
            termo = f"%{termo_busca}%"

            lista_unidades = conn.execute("""
                SELECT *
                FROM unidades
                WHERE codigo LIKE ?
                OR nome LIKE ?
                OR grupo_rede LIKE ?
                OR tipo_unidade LIKE ?
                OR endereco LIKE ?
                ORDER BY nome
            """, (
                termo,
                termo,
                termo,
                termo,
                termo
            )).fetchall()
        else:
            lista_unidades = conn.execute("""
                SELECT *
                FROM unidades
                ORDER BY nome
            """).fetchall()

    return render_template(
        "unidades.html",
        unidades=lista_unidades,
        busca=termo_busca
    )

@app.route("/unidades/<int:id_unidade>/editar", methods=["GET", "POST"])
@login_required
def editar_unidade(id_unidade):
    """Edita uma unidade cadastrada."""

    with get_db_connection() as conn:
        unidade = conn.execute("""
            SELECT *
            FROM unidades
            WHERE id_unidade = ?
        """, (id_unidade,)).fetchone()

    if unidade is None:
        flash("Unidade não encontrada.", "erro")
        return redirect(url_for("unidades"))

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip().upper()
        nome = request.form.get("nome", "").strip()
        grupo_rede = request.form.get("grupo_rede", "").strip()
        tipo_unidade = request.form.get("tipo_unidade", "").strip()
        endereco = request.form.get("endereco", "").strip()

        if not codigo or not nome or not grupo_rede or not tipo_unidade:
            flash(
                "Código, nome, grupo da rede e tipo de unidade são obrigatórios.",
                "erro"
            )

            unidade = {
                "id_unidade": id_unidade,
                "codigo": codigo,
                "nome": nome,
                "grupo_rede": grupo_rede,
                "tipo_unidade": tipo_unidade,
                "endereco": endereco
            }

            return render_template(
                "editar_unidade.html",
                unidade=unidade
            )

        try:
            with get_db_connection() as conn:
                conn.execute("""
                    UPDATE unidades
                    SET
                        codigo = ?,
                        nome = ?,
                        grupo_rede = ?,
                        tipo_unidade = ?,
                        endereco = ?
                    WHERE id_unidade = ?
                """, (
                    codigo,
                    nome,
                    grupo_rede,
                    tipo_unidade,
                    endereco,
                    id_unidade
                ))

            flash("Unidade atualizada com sucesso!", "sucesso")
            return redirect(url_for("unidades"))

        except sqlite3.IntegrityError:
            flash(
                "Já existe outra unidade cadastrada com este código.",
                "erro"
            )

        except sqlite3.Error as erro_banco:
            flash(
                f"Erro ao atualizar a unidade: {erro_banco}",
                "erro"
            )

        unidade = {
            "id_unidade": id_unidade,
            "codigo": codigo,
            "nome": nome,
            "grupo_rede": grupo_rede,
            "tipo_unidade": tipo_unidade,
            "endereco": endereco
        }

    return render_template(
        "editar_unidade.html",
        unidade=unidade
    )

@app.route("/unidades/<int:id_unidade>/excluir", methods=["POST"])
@login_required
def excluir_unidade(id_unidade):
    """Exclui uma unidade apenas quando não há registros vinculados."""

    try:
        with get_db_connection() as conn:
            unidade = conn.execute(
                """
                SELECT id_unidade, codigo, nome
                FROM unidades
                WHERE id_unidade = ?
                """,
                (id_unidade,),
            ).fetchone()

            if unidade is None:
                flash("Unidade não encontrada.", "erro")
                return redirect(url_for("unidades"))

            total_equipamentos = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM equipamentos
                WHERE id_unidade = ?
                """,
                (id_unidade,),
            ).fetchone()["total"]

            total_insumos = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM insumos
                WHERE id_unidade = ?
                """,
                (id_unidade,),
            ).fetchone()["total"]

            if total_equipamentos > 0 or total_insumos > 0:
                flash(
                    "Não é possível excluir esta unidade porque ela possui "
                    f"{total_equipamentos} equipamento(s) e "
                    f"{total_insumos} insumo(s) vinculados. "
                    "Edite ou exclua esses registros antes de excluir a unidade.",
                    "erro",
                )
                return redirect(url_for("unidades"))

            conn.execute(
                """
                DELETE FROM unidades
                WHERE id_unidade = ?
                """,
                (id_unidade,),
            )

        flash("Unidade excluída com sucesso!", "sucesso")

    except sqlite3.Error as erro_banco:
        flash(
            f"Não foi possível excluir a unidade: {erro_banco}",
            "erro",
        )

    return redirect(url_for("unidades"))
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

@app.route("/equipamentos/<int:id_equipamento>/editar", methods=["GET", "POST"])
@login_required
def editar_equipamento(id_equipamento):
    """Edita um equipamento cadastrado."""

    with get_db_connection() as conn:
        equipamento = conn.execute(
            """
            SELECT *
            FROM equipamentos
            WHERE id_equipamento = ?
            """,
            (id_equipamento,),
        ).fetchone()

        lista_unidades = conn.execute(
            """
            SELECT id_unidade, codigo, nome
            FROM unidades
            ORDER BY nome
            """
        ).fetchall()

    if equipamento is None:
        flash("Equipamento não encontrado.", "erro")
        return redirect(url_for("equipamentos"))

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
                "erro",
            )
        else:
            try:
                with get_db_connection() as conn:
                    conn.execute(
                        """
                        UPDATE equipamentos
                        SET
                            id_unidade = ?,
                            patrimonio = ?,
                            nome = ?,
                            modelo = ?,
                            marca = ?,
                            numero_serie = ?,
                            data_entrada = ?,
                            situacao = ?,
                            observacao = ?
                        WHERE id_equipamento = ?
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
                            id_equipamento,
                        ),
                    )

                flash("Equipamento atualizado com sucesso!", "sucesso")
                return redirect(url_for("equipamentos"))

            except sqlite3.IntegrityError:
                flash(
                    "Já existe outro equipamento com este patrimônio nesta unidade.",
                    "erro",
                )

        equipamento = {
            "id_equipamento": id_equipamento,
            "id_unidade": id_unidade,
            "patrimonio": patrimonio,
            "nome": nome,
            "modelo": modelo,
            "marca": marca,
            "numero_serie": numero_serie,
            "data_entrada": data_entrada,
            "situacao": situacao,
            "observacao": observacao,
        }

    return render_template(
        "editar_equipamento.html",
        equipamento=equipamento,
        unidades=lista_unidades,
    )

@app.route("/equipamentos/<int:id_equipamento>/excluir", methods=["POST"])
@login_required
def excluir_equipamento(id_equipamento):
    """Exclui um equipamento cadastrado."""

    try:
        with get_db_connection() as conn:
            equipamento = conn.execute(
                """
                SELECT id_equipamento, nome, patrimonio
                FROM equipamentos
                WHERE id_equipamento = ?
                """,
                (id_equipamento,),
            ).fetchone()

            if equipamento is None:
                flash("Equipamento não encontrado.", "erro")
                return redirect(url_for("equipamentos"))

            conn.execute(
                """
                DELETE FROM equipamentos
                WHERE id_equipamento = ?
                """,
                (id_equipamento,),
            )

        flash("Equipamento excluído com sucesso!", "sucesso")

    except sqlite3.Error as erro_banco:
        flash(
            f"Não foi possível excluir o equipamento: {erro_banco}",
            "erro",
        )

    return redirect(url_for("equipamentos"))

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

@app.route("/insumos/<int:id_insumo>/editar", methods=["GET", "POST"])
@login_required
def editar_insumo(id_insumo):
    """Edita um insumo cadastrado."""

    with get_db_connection() as conn:
        insumo = conn.execute(
            """
            SELECT *
            FROM insumos
            WHERE id_insumo = ?
            """,
            (id_insumo,),
        ).fetchone()

        lista_unidades = conn.execute(
            """
            SELECT id_unidade, codigo, nome
            FROM unidades
            ORDER BY nome
            """
        ).fetchall()

    if insumo is None:
        flash("Insumo não encontrado.", "erro")
        return redirect(url_for("insumos"))

    if request.method == "POST":
        id_unidade_texto = request.form.get("id_unidade", "").strip()

        if id_unidade_texto:
            try:
                id_unidade = int(id_unidade_texto)
            except ValueError:
                id_unidade = None
        else:
            # Vazio representa o Almoxarifado Central.
            id_unidade = None

        modelo = request.form.get("modelo", "").strip()
        marca = request.form.get("marca", "").strip()
        numero_serie = request.form.get("numero_serie", "").strip()
        quantidade_texto = request.form.get("quantidade", "0").strip()

        try:
            quantidade = int(quantidade_texto)
        except ValueError:
            quantidade = -1

        data_entrega = request.form.get("data_entrega", "").strip() or None
        data_fabricacao = request.form.get(
            "data_fabricacao",
            "",
        ).strip() or None
        vencimento = request.form.get("vencimento", "").strip() or None
        localizacao = request.form.get("localizacao", "").strip()
        observacao = request.form.get("observacao", "").strip()

        if not modelo or not marca:
            flash("Modelo e marca são obrigatórios.", "erro")

        elif quantidade < 0:
            flash(
                "A quantidade deve ser um número inteiro igual ou maior que zero.",
                "erro",
            )

        else:
            try:
                with get_db_connection() as conn:
                    conn.execute(
                        """
                        UPDATE insumos
                        SET
                            id_unidade = ?,
                            modelo = ?,
                            marca = ?,
                            numero_serie = ?,
                            quantidade = ?,
                            data_entrega = ?,
                            data_fabricacao = ?,
                            vencimento = ?,
                            localizacao = ?,
                            observacao = ?
                        WHERE id_insumo = ?
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
                            id_insumo,
                        ),
                    )

                flash("Insumo atualizado com sucesso!", "sucesso")
                return redirect(url_for("insumos"))

            except sqlite3.Error as erro_banco:
                flash(
                    f"Erro ao atualizar insumo: {erro_banco}",
                    "erro",
                )

        # Mantém os dados digitados caso haja erro de validação.
        insumo = {
            "id_insumo": id_insumo,
            "id_unidade": id_unidade,
            "modelo": modelo,
            "marca": marca,
            "numero_serie": numero_serie,
            "quantidade": quantidade_texto,
            "data_entrega": data_entrega,
            "data_fabricacao": data_fabricacao,
            "vencimento": vencimento,
            "localizacao": localizacao,
            "observacao": observacao,
        }

    return render_template(
        "editar_insumo.html",
        insumo=insumo,
        unidades=lista_unidades,
    )

@app.route("/insumos/<int:id_insumo>/excluir", methods=["POST"])
@login_required
def excluir_insumo(id_insumo):
    """Exclui um insumo cadastrado."""

    try:
        with get_db_connection() as conn:
            insumo = conn.execute(
                """
                SELECT id_insumo, modelo, marca
                FROM insumos
                WHERE id_insumo = ?
                """,
                (id_insumo,),
            ).fetchone()

            if insumo is None:
                flash("Insumo não encontrado.", "erro")
                return redirect(url_for("insumos"))

            conn.execute(
                """
                DELETE FROM insumos
                WHERE id_insumo = ?
                """,
                (id_insumo,),
            )

        flash("Insumo excluído com sucesso!", "sucesso")

    except sqlite3.Error as erro_banco:
        flash(
            f"Não foi possível excluir o insumo: {erro_banco}",
            "erro",
        )

    return redirect(url_for("insumos"))


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
                u.grupo_rede,
                u.tipo_unidade,
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
                u.grupo_rede,
                u.tipo_unidade,
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

        relatorio_os = conn.execute(
            """
            SELECT
                os.id_os,
                os.numero_os,
                os.empresa_prestadora,
                os.solicitante,
                os.tipo_servico,
                os.problema_relatado,
                os.status,
                os.data_abertura,
                os.data_conclusao,

                u.codigo AS codigo_unidade,
                u.nome AS nome_unidade,

                e.patrimonio,
                e.nome AS nome_equipamento,
                e.modelo AS modelo_equipamento,
                e.marca AS marca_equipamento,

                usuario.nome AS cadastrado_por,

                COUNT(anexo.id_anexo) AS total_anexos

            FROM ordens_servico AS os

            LEFT JOIN unidades AS u
                ON u.id_unidade = os.id_unidade

            LEFT JOIN equipamentos AS e
                ON e.id_equipamento = os.id_equipamento

            LEFT JOIN usuarios AS usuario
                ON usuario.id_usuario = os.criado_por

            LEFT JOIN anexos_ordem_servico AS anexo
                ON anexo.id_os = os.id_os

            GROUP BY
                os.id_os,
                os.numero_os,
                os.empresa_prestadora,
                os.solicitante,
                os.tipo_servico,
                os.problema_relatado,
                os.status,
                os.data_abertura,
                os.data_conclusao,
                u.codigo,
                u.nome,
                e.patrimonio,
                e.nome,
                e.modelo,
                e.marca,
                usuario.nome

            ORDER BY
                CASE os.status
                    WHEN 'Aberta' THEN 1
                    WHEN 'Em andamento' THEN 2
                    WHEN 'Aguardando peça' THEN 3
                    WHEN 'Concluída' THEN 4
                    WHEN 'Cancelada' THEN 5
                    ELSE 6
                END,
                os.data_abertura DESC,
                os.id_os DESC
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

        resumo_os = conn.execute(
            """
            SELECT
                COUNT(*) AS total_os,

                SUM(
                    CASE
                        WHEN status = 'Aberta'
                        THEN 1
                        ELSE 0
                    END
                ) AS abertas,

                SUM(
                    CASE
                        WHEN status = 'Em andamento'
                        THEN 1
                        ELSE 0
                    END
                ) AS em_andamento,

                SUM(
                    CASE
                        WHEN status = 'Aguardando peça'
                        THEN 1
                        ELSE 0
                    END
                ) AS aguardando_peca,

                SUM(
                    CASE
                        WHEN status = 'Concluída'
                        THEN 1
                        ELSE 0
                    END
                ) AS concluidas,

                SUM(
                    CASE
                        WHEN status = 'Cancelada'
                        THEN 1
                        ELSE 0
                    END
                ) AS canceladas

            FROM ordens_servico
            """
        ).fetchone()

    return render_template(
        "relatorios.html",
        resumo=resumo,
        resumo_os=resumo_os,
        relatorio_unidades=relatorio_unidades,
        relatorio_equipamentos=relatorio_equipamentos,
        relatorio_insumos=relatorio_insumos,
        relatorio_os=relatorio_os,
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
        u.grupo_rede,
        u.tipo_unidade,
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
        u.grupo_rede,
        u.tipo_unidade,
        u.endereco
    ORDER BY u.nome
    """
).fetchall()

    cabecalhos = [
    "Código",
    "Nome da unidade",
    "Grupo da rede",
    "Tipo de unidade",
    "Endereço",
    "Total de equipamentos",
    "Total de insumos",
]

    linhas = [
    [
        unidade["codigo"],
        unidade["nome"],
        unidade["grupo_rede"] or "-",
        unidade["tipo_unidade"] or "-",
        unidade["endereco"] or "-",
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

def atualizar_banco_unidades():
    """Adiciona as novas colunas à tabela unidades."""

    with get_db_connection() as conn:
        colunas = [
            coluna["name"]
            for coluna in conn.execute(
                "PRAGMA table_info(unidades)"
            ).fetchall()
        ]

        if "grupo_rede" not in colunas:
            conn.execute("""
                ALTER TABLE unidades
                ADD COLUMN grupo_rede TEXT
            """)

        if "tipo_unidade" not in colunas:
            conn.execute("""
                ALTER TABLE unidades
                ADD COLUMN tipo_unidade TEXT
            """)

        conn.commit()

def atualizar_banco_usuarios():
    with get_db_connection() as conn:
        colunas = [
            linha["name"]
            for linha in conn.execute(
                "PRAGMA table_info(usuarios)"
            ).fetchall()
        ]

        if "ultimo_acesso" not in colunas:
            conn.execute(
                "ALTER TABLE usuarios ADD COLUMN ultimo_acesso TEXT"
            )

def redefinir_senhas_iniciais():
    """Redefine temporariamente as senhas dos três usuários institucionais."""

    usuarios = [
        (
            "alexandre.silverio@treslagoas.ms.gov.br",
            "Almox@Alexandre2026",
        ),
        (
            "marcio.martins@treslagoas.ms.gov.br",
            "Almox@Marcio2026",
        ),
        (
            "alessandra.paula@treslagoas.ms.gov.br",
            "Almox@Alessandra2026",
        ),
    ]

    with get_db_connection() as conn:
        for email, senha in usuarios:
            conn.execute(
                """
                UPDATE usuarios
                SET
                    senha_hash = ?,
                    ativo = 1,
                    primeiro_acesso = 1
                WHERE email = ?
                """,
                (
                    generate_password_hash(senha),
                    email,
                ),
            )

# =========================================================
# CONFIGURAÇÕES — CONTROLE DE ACESSO
# =========================================================

def login_obrigatorio(funcao):
    @wraps(funcao)
    def decorada(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Faça login para acessar o sistema.", "erro")

            return redirect(
                url_for(
                    "login",
                    next=request.path,
                )
            )

        return funcao(*args, **kwargs)

    return decorada


def administrador_obrigatorio(funcao):
    @wraps(funcao)
    def decorada(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Faça login para acessar o sistema.", "erro")
            return redirect(url_for("login", next=request.path))

        papeis_autorizados = {
            "administrador",
            "administrador_principal",
        }

        papel_usuario = session.get(
            "papel_usuario",
            "",
        ).strip().lower()

        if papel_usuario not in papeis_autorizados:
            abort(403)

        return funcao(*args, **kwargs)

    return decorada

def arquivo_pdf_permitido(arquivo):
    """Verifica se o arquivo enviado possui extensão PDF."""

    if arquivo is None:
        return False

    if not arquivo.filename:
        return False

    if "." not in arquivo.filename:
        return False

    extensao = arquivo.filename.rsplit(".", 1)[1].lower()

    return extensao in ALLOWED_OS_EXTENSIONS

@app.errorhandler(413)
def arquivo_muito_grande(erro):
    """Exibe mensagem amigável para upload acima de 10 MB."""

    flash(
        "O arquivo enviado é maior que o limite de 10 MB.",
        "erro",
    )

    return redirect(
        request.referrer or url_for("ordens_servico")
    )

@app.route("/configuracoes")
@administrador_obrigatorio
def configuracoes():
    with get_db_connection() as conn:
        usuarios = conn.execute(
            """
            SELECT
                id_usuario,
                nome,
                email,
                papel,
                ativo,
                primeiro_acesso,
                criado_em
            FROM usuarios
            ORDER BY nome COLLATE NOCASE
            """
        ).fetchall()

    return render_template(
        "configuracoes.html",
        usuarios=usuarios,
    )

@app.route("/primeiro-acesso", methods=["GET", "POST"])
@login_obrigatorio
def primeiro_acesso():
    """Obriga o usuário a substituir a senha temporária."""

    if not session.get("primeiro_acesso"):
        return redirect(url_for("index"))

    erro = None

    if request.method == "POST":
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not nova_senha or not confirmar_senha:
            erro = "Preencha os dois campos de senha."

        elif len(nova_senha) < 8:
            erro = "A nova senha deve ter pelo menos 8 caracteres."

        elif nova_senha != confirmar_senha:
            erro = "A confirmação de senha não confere."

        else:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    UPDATE usuarios
                    SET
                        senha_hash = ?,
                        primeiro_acesso = 0
                    WHERE id_usuario = ?
                    """,
                    (
                        generate_password_hash(nova_senha),
                        session["id_usuario"],
                    ),
                )

            session["primeiro_acesso"] = 0

            flash(
                "Senha criada com sucesso. Bem-vindo(a) ao sistema!",
                "sucesso",
            )

            return redirect(url_for("index"))

    return render_template(
        "primeiro_acesso.html",
        erro=erro,
    )


from functools import wraps

def senha_atualizada_obrigatoria(funcao):
    @wraps(funcao)
    def decorada(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))

        if session.get("primeiro_acesso"):
            flash(
                "Por segurança, defina uma nova senha para continuar.",
                "aviso",
            )
            return redirect(url_for("primeiro_acesso"))

        return funcao(*args, **kwargs)

    return decorada

@app.route("/minha-conta", methods=["GET", "POST"])
@login_obrigatorio
@senha_atualizada_obrigatoria
def minha_conta():
    """Permite que o usuário atualize apenas seus próprios dados."""

    usuario_id = session["id_usuario"]
    erro = None

    with get_db_connection() as conn:
        usuario = conn.execute(
            """
            SELECT
                id_usuario,
                nome,
                email,
                papel
            FROM usuarios
            WHERE id_usuario = ?
            """,
            (usuario_id,),
        ).fetchone()

    if usuario is None:
        session.clear()

        flash(
            "Sua sessão não é mais válida. Faça login novamente.",
            "erro",
        )

        return redirect(url_for("login"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not nome:
            erro = "Informe seu nome completo."

        elif not email:
            erro = "Informe seu e-mail institucional."

        else:
            try:
                with get_db_connection() as conn:
                    conn.execute(
                        """
                        UPDATE usuarios
                        SET
                            nome = ?,
                            email = ?
                        WHERE id_usuario = ?
                        """,
                        (
                            nome,
                            email,
                            usuario_id,
                        ),
                    )

                session["nome_usuario"] = nome
                session["email_usuario"] = email

                flash(
                    "Seus dados foram atualizados com sucesso.",
                    "sucesso",
                )

                return redirect(url_for("minha_conta"))

            except sqlite3.IntegrityError:
                erro = (
                    "Este e-mail já está cadastrado para outro usuário."
                )

        usuario = {
            "id_usuario": usuario_id,
            "nome": nome,
            "email": email,
            "papel": usuario["papel"],
        }

    return render_template(
        "minha_conta.html",
        usuario=usuario,
        erro=erro,
    )

@app.route("/minha-conta/alterar-senha", methods=["GET", "POST"])
@login_obrigatorio
@senha_atualizada_obrigatoria
def alterar_minha_senha():
    """Permite que o usuário logado altere sua própria senha."""

    erro = None
    usuario_id = session["id_usuario"]

    if request.method == "POST":
        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not senha_atual:
            erro = "Informe sua senha atual."

        elif not nova_senha or not confirmar_senha:
            erro = "Preencha a nova senha e a confirmação."

        elif len(nova_senha) < 8:
            erro = "A nova senha deve ter pelo menos 8 caracteres."

        elif nova_senha != confirmar_senha:
            erro = "A confirmação de senha não confere."

        elif nova_senha == senha_atual:
            erro = "A nova senha deve ser diferente da senha atual."

        else:
            with get_db_connection() as conn:
                usuario = conn.execute(
                    """
                    SELECT senha_hash
                    FROM usuarios
                    WHERE id_usuario = ?
                    """,
                    (usuario_id,),
                ).fetchone()

                if usuario is None:
                    session.clear()

                    flash(
                        "Sua sessão não é mais válida. Faça login novamente.",
                        "erro",
                    )

                    return redirect(url_for("login"))

                if not check_password_hash(
                    usuario["senha_hash"],
                    senha_atual,
                ):
                    erro = "A senha atual está incorreta."

                else:
                    conn.execute(
                        """
                        UPDATE usuarios
                        SET senha_hash = ?
                        WHERE id_usuario = ?
                        """,
                        (
                            generate_password_hash(nova_senha),
                            usuario_id,
                        ),
                    )

                    flash(
                        "Sua senha foi alterada com sucesso.",
                        "sucesso",
                    )

                    return redirect(url_for("minha_conta"))

    return render_template(
        "alterar_senha.html",
        erro=erro,
    )

@app.route("/ordens-servico")
@login_obrigatorio
@senha_atualizada_obrigatoria
def ordens_servico():
    """Lista as ordens de serviço cadastradas."""

    busca = request.args.get("busca", "").strip()
    status = request.args.get("status", "").strip()

    sql = """
        SELECT
            os.id_os,
            os.numero_os,
            os.empresa_prestadora,
            os.solicitante,
            os.tipo_servico,
            os.problema_relatado,
            os.status,
            os.data_abertura,
            os.data_conclusao,

            u.nome AS nome_unidade,

            e.nome AS nome_equipamento,
            e.patrimonio,

            a.id_anexo

        FROM ordens_servico AS os

        LEFT JOIN unidades AS u
            ON u.id_unidade = os.id_unidade

        LEFT JOIN equipamentos AS e
            ON e.id_equipamento = os.id_equipamento

        LEFT JOIN anexos_ordem_servico AS a
            ON a.id_os = os.id_os

        WHERE 1 = 1
    """

    parametros = []

    if busca:
        sql += """
            AND (
                os.numero_os LIKE ?
                OR os.empresa_prestadora LIKE ?
                OR os.solicitante LIKE ?
                OR u.nome LIKE ?
                OR e.nome LIKE ?
                OR e.patrimonio LIKE ?
            )
        """

        termo_busca = f"%{busca}%"

        parametros.extend(
            [
                termo_busca,
                termo_busca,
                termo_busca,
                termo_busca,
                termo_busca,
                termo_busca,
            ]
        )

    if status:
        sql += " AND os.status = ? "
        parametros.append(status)

    sql += """
        ORDER BY
            CASE os.status
                WHEN 'Aberta' THEN 1
                WHEN 'Em andamento' THEN 2
                WHEN 'Aguardando peça' THEN 3
                WHEN 'Concluída' THEN 4
                WHEN 'Cancelada' THEN 5
                ELSE 6
            END,
            os.data_abertura DESC,
            os.id_os DESC
    """

    with get_db_connection() as conn:
        ordens = conn.execute(sql, parametros).fetchall()

        resumo = conn.execute(
            """
            SELECT
                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN status = 'Aberta'
                        THEN 1
                        ELSE 0
                    END
                ) AS abertas,

                SUM(
                    CASE
                        WHEN status = 'Em andamento'
                        THEN 1
                        ELSE 0
                    END
                ) AS em_andamento,

                SUM(
                    CASE
                        WHEN status = 'Aguardando peça'
                        THEN 1
                        ELSE 0
                    END
                ) AS aguardando_peca,

                SUM(
                    CASE
                        WHEN status = 'Concluída'
                        THEN 1
                        ELSE 0
                    END
                ) AS concluidas

            FROM ordens_servico
            """
        ).fetchone()

    return render_template(
        "ordens_servico.html",
        ordens=ordens,
        resumo=resumo,
        busca=busca,
        status_atual=status,
    )

@app.route("/ordens-servico/nova", methods=["GET", "POST"])
@login_obrigatorio
@senha_atualizada_obrigatoria
@administrador_obrigatorio
def nova_ordem_servico():
    """Cadastra uma ordem de serviço e anexa seu PDF original."""

    erro = None

    with get_db_connection() as conn:
        unidades = conn.execute(
            """
            SELECT
                id_unidade,
                nome
            FROM unidades
            ORDER BY nome
            """
        ).fetchall()

        equipamentos = conn.execute(
            """
            SELECT
                id_equipamento,
                nome,
                patrimonio
            FROM equipamentos
            ORDER BY nome
            """
        ).fetchall()

    if request.method == "POST":
        numero_os = request.form.get("numero_os", "").strip()

        empresa_prestadora = request.form.get(
            "empresa_prestadora",
            "",
        ).strip()

        id_unidade = request.form.get("id_unidade", "").strip()

        id_equipamento = request.form.get(
            "id_equipamento",
            "",
        ).strip()

        solicitante = request.form.get("solicitante", "").strip()

        tipo_servico = request.form.get(
            "tipo_servico",
            "",
        ).strip()

        problema_relatado = request.form.get(
            "problema_relatado",
            "",
        ).strip()

        observacoes = request.form.get(
            "observacoes",
            "",
        ).strip()

        status = request.form.get(
            "status",
            "Aberta",
        ).strip()

        data_abertura = request.form.get(
            "data_abertura",
            "",
        ).strip()

        arquivo_os = request.files.get("arquivo_os")

        status_validos = {
            "Aberta",
            "Em andamento",
            "Aguardando peça",
            "Concluída",
            "Cancelada",
        }

        if not numero_os:
            erro = "Informe o número da ordem de serviço."

        elif not empresa_prestadora:
            erro = "Informe a empresa prestadora."

        elif not solicitante:
            erro = "Informe o solicitante."

        elif not tipo_servico:
            erro = "Informe o tipo de serviço."

        elif status not in status_validos:
            erro = "Informe um status válido."

        elif not data_abertura:
            erro = "Informe a data de abertura."

        elif not id_unidade:
            erro = "Selecione a unidade."

        elif not id_equipamento:
            erro = "Selecione o equipamento."

        elif not arquivo_pdf_permitido(arquivo_os):
            erro = "Anexe um arquivo PDF válido da ordem de serviço."

        if erro is None:
            nome_original = arquivo_os.filename
            nome_seguro = secure_filename(nome_original)

            if not nome_seguro:
                nome_seguro = "ordem_servico.pdf"

            nome_arquivo = (
                f"os_{uuid4().hex}_{nome_seguro}"
            )

            caminho_completo = os.path.join(
                app.config["UPLOAD_OS_FOLDER"],
                nome_arquivo,
            )

            try:
                id_unidade = int(id_unidade)

                id_equipamento = int(id_equipamento)

                data_abertura_formatada = datetime.strptime(
                    data_abertura,
                    "%Y-%m-%dT%H:%M",
                ).strftime("%Y-%m-%d %H:%M:%S")

            except ValueError:
                erro = (
                    "Confira a unidade, o equipamento "
                    "e a data de abertura."
                )

            if erro is None:
                try:
                    arquivo_os.save(caminho_completo)

                    tamanho_bytes = os.path.getsize(
                        caminho_completo
                    )

                    with get_db_connection() as conn:
                        cursor = conn.execute(
                            """
                            INSERT INTO ordens_servico (
                                numero_os,
                                empresa_prestadora,
                                id_unidade,
                                id_equipamento,
                                solicitante,
                                tipo_servico,
                                problema_relatado,
                                observacoes,
                                status,
                                data_abertura,
                                criado_por
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                numero_os,
                                empresa_prestadora,
                                id_unidade,
                                id_equipamento,
                                solicitante,
                                tipo_servico,
                                problema_relatado,
                                observacoes,
                                status,
                                data_abertura_formatada,
                                session["id_usuario"],
                            ),
                        )

                        id_os = cursor.lastrowid

                        conn.execute(
                            """
                            INSERT INTO anexos_ordem_servico (
                                id_os,
                                nome_original,
                                nome_arquivo,
                                caminho_arquivo,
                                tipo_arquivo,
                                tamanho_bytes
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                id_os,
                                nome_original,
                                nome_arquivo,
                                nome_arquivo,
                                "application/pdf",
                                tamanho_bytes,
                            ),
                        )

                    flash(
                        "Ordem de serviço cadastrada com sucesso.",
                        "sucesso",
                    )

                    return redirect(
                        url_for(
                            "detalhe_ordem_servico",
                            id_os=id_os,
                        )
                    )

                except sqlite3.IntegrityError:
                    if os.path.exists(caminho_completo):
                        os.remove(caminho_completo)

                    erro = (
                        "Já existe uma OS com esse número "
                        "para esta empresa."
                    )

                except OSError:
                    if os.path.exists(caminho_completo):
                        os.remove(caminho_completo)

                    erro = (
                        "Não foi possível salvar o PDF enviado. "
                        "Tente novamente."
                    )

    return render_template(
        "nova_ordem_servico.html",
        unidades=unidades,
        equipamentos=equipamentos,
        erro=erro,
    )

@app.route(
    "/ordens-servico/<int:id_os>",
    methods=["GET", "POST"],
)
@login_obrigatorio
@senha_atualizada_obrigatoria
def detalhe_ordem_servico(id_os):
    """Mostra uma OS e permite atualizar seu andamento."""

    erro = None

    status_validos = {
        "Aberta",
        "Em andamento",
        "Aguardando peça",
        "Concluída",
        "Cancelada",
    }

    if request.method == "POST":
        papel_atual = session.get(
            "papel_usuario",
            "",
        ).strip().lower()

        if papel_atual not in {
            "administrador",
            "administrador_principal",
        }:
            flash(
                "Somente administradores podem atualizar uma OS.",
                "erro",
            )

            return redirect(
                url_for(
                    "detalhe_ordem_servico",
                    id_os=id_os,
                )
            )

        status = request.form.get("status", "").strip()

        observacoes = request.form.get(
            "observacoes",
            "",
        ).strip()

        if status not in status_validos:
            erro = "Selecione um status válido."

        else:
            data_conclusao = None

            if status == "Concluída":
                data_conclusao = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            with get_db_connection() as conn:
                conn.execute(
                    """
                    UPDATE ordens_servico
                    SET
                        status = ?,
                        observacoes = ?,
                        data_conclusao = ?
                    WHERE id_os = ?
                    """,
                    (
                        status,
                        observacoes,
                        data_conclusao,
                        id_os,
                    ),
                )

            flash(
                "Ordem de serviço atualizada com sucesso.",
                "sucesso",
            )

            return redirect(
                url_for(
                    "detalhe_ordem_servico",
                    id_os=id_os,
                )
            )

    with get_db_connection() as conn:
        ordem = conn.execute(
            """
            SELECT
                os.*,

                u.nome AS nome_unidade,

                e.nome AS nome_equipamento,
                e.patrimonio,

                usuario.nome AS nome_criador

            FROM ordens_servico AS os

            LEFT JOIN unidades AS u
                ON u.id_unidade = os.id_unidade

            LEFT JOIN equipamentos AS e
                ON e.id_equipamento = os.id_equipamento

            LEFT JOIN usuarios AS usuario
                ON usuario.id_usuario = os.criado_por

            WHERE os.id_os = ?
            """,
            (id_os,),
        ).fetchone()

        anexos = conn.execute(
            """
            SELECT
                id_anexo,
                nome_original,
                tipo_arquivo,
                tamanho_bytes,
                enviado_em
            FROM anexos_ordem_servico
            WHERE id_os = ?
            ORDER BY enviado_em DESC
            """,
            (id_os,),
        ).fetchall()

    if ordem is None:
        flash(
            "Ordem de serviço não encontrada.",
            "erro",
        )

        return redirect(url_for("ordens_servico"))

    return render_template(
        "detalhe_ordem_servico.html",
        ordem=ordem,
        anexos=anexos,
        erro=erro,
    )

@app.route(
    "/ordens-servico/anexos/<int:id_anexo>/download"
)
@login_obrigatorio
@senha_atualizada_obrigatoria
def baixar_anexo_ordem_servico(id_anexo):
    """Faz download protegido de um PDF de OS."""

    with get_db_connection() as conn:
        anexo = conn.execute(
            """
            SELECT
                nome_original,
                nome_arquivo
            FROM anexos_ordem_servico
            WHERE id_anexo = ?
            """,
            (id_anexo,),
        ).fetchone()

    if anexo is None:
        flash(
            "Anexo não encontrado.",
            "erro",
        )

        return redirect(url_for("ordens_servico"))

    return send_from_directory(
        app.config["UPLOAD_OS_FOLDER"],
        anexo["nome_arquivo"],
        as_attachment=True,
        download_name=anexo["nome_original"],
    )


if __name__ == "__main__":
    init_db()
    atualizar_banco_usuarios()
    atualizar_banco_unidades()
    criar_usuarios_iniciais()
    app.run(debug=True)