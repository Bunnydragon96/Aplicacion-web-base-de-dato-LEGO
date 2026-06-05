"""
app.py  ──  Capa CONTROLADOR (rutas Flask) del patrón MVC.

Orquesta las peticiones entre el Modelo (db.py) y las Vistas (templates Jinja2).
Incluye autenticación con Flask-Login y hashing de contraseñas con Werkzeug,
según el documento de diseño.

Arranque:
    python etl.py        # genera lego.db (una sola vez)
    python app.py        # levanta el servidor de desarrollo
    -> http://127.0.0.1:5000
"""
from flask import (Flask, render_template, request, redirect, url_for, flash)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

import db

app = Flask(__name__)
app.config["SECRET_KEY"] = "cambia-esto-en-produccion"  # para sesiones/CSRF flash

csrf = CSRFProtect(app)   # protección CSRF global para todos los formularios POST

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Debes iniciar sesión para acceder."


# ---------- Integración con Flask-Login ------------------------------------
class User(UserMixin):
    def __init__(self, row):
        self.id = str(row["user_id"])
        self.username = row["username"]


@login_manager.user_loader
def load_user(user_id):
    row = db.get_user_by_id(int(user_id))
    return User(row) if row else None


# ====================================================================== #
#  RF-01 / RF-02  ── Registro y autenticación                            #
# ====================================================================== #
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        if not u or not p:
            flash("Usuario y contraseña son obligatorios.", "error")
        elif len(p) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.", "error")
        elif db.get_user_by_name(u):
            flash("Ese usuario ya existe.", "error")
        else:
            db.create_user(u, generate_password_hash(p))
            flash("Cuenta creada. Ya puedes iniciar sesión.", "ok")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        row = db.get_user_by_name(u)
        if row and check_password_hash(row["password_hash"], p):
            login_user(User(row))
            return redirect(url_for("index"))
        flash("Credenciales inválidas.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ====================================================================== #
#  Inicio                                                                #
# ====================================================================== #
@app.route("/")
@login_required
def index():
    return render_template("index.html")


# ---------- RF-04: todas las tablas ----------------------------------------
@app.route("/tablas")
@login_required
def tablas():
    return render_template("tablas.html", tablas=db.all_tables())


# ---------- RF-05: escoger un atributo de una relación ---------------------
@app.route("/atributo")
@login_required
def atributo():
    table = request.args.get("table", "")
    column = request.args.get("column", "")
    cols = rows = None
    error = None
    if table and column:
        try:
            cols, rows = db.project_attribute(table, column)
        except ValueError as e:
            error = str(e)
    return render_template("atributo.html", projectable=db.PROJECTABLE,
                           sel_table=table, sel_col=column,
                           cols=cols, rows=rows, error=error)


# ---------- RF-06: JOIN de 3+ tablas ---------------------------------------
@app.route("/join")
@login_required
def join():
    theme_id = request.args.get("theme_id", type=int)
    cols, rows = db.join_sets(theme_id=theme_id)
    return render_template("join.html", themes=db.list_themes(),
                           sel_theme=theme_id, cols=cols, rows=rows)


# ---------- RF-07: agregación GROUP BY/HAVING ------------------------------
@app.route("/agregacion")
@login_required
def agregacion():
    country = request.args.get("country", "US")
    min_sets = request.args.get("min_sets", default=10, type=int)
    cols, rows = db.avg_price_by_theme(country, min_sets)
    return render_template("agregacion.html", countries=db.list_countries(),
                           sel_country=country, min_sets=min_sets,
                           cols=cols, rows=rows)


# ---------- RF-03: subconsulta (WITH) --------------------------------------
@app.route("/subconsulta")
@login_required
def subconsulta():
    country = request.args.get("country", "US")
    cols, rows = db.sets_above_avg_price(country)
    return render_template("subconsulta.html", countries=db.list_countries(),
                           sel_country=country, cols=cols, rows=rows)


# ---------- RF-08: insertar -------------------------------------------------
@app.route("/insertar", methods=["GET", "POST"])
@login_required
def insertar():
    if request.method == "POST":
        try:
            new_id = db.insert_set(
                request.form["set_name"].strip(),
                request.form.get("piece_count", type=int),
                request.form.get("theme_id", type=int),
                request.form.get("age_id", type=int),
                request.form.get("difficulty_id", type=int),
            )
            flash(f"Set insertado con prod_id = {new_id}.", "ok")
            return redirect(url_for("modificar", prod_id=new_id))
        except Exception as e:
            flash(f"Error al insertar: {e}", "error")
    return render_template("insertar.html", themes=db.list_themes(),
                           ages=db.list_ages(), diffs=db.list_difficulties())


# ---------- RF-09: modificar ------------------------------------------------
@app.route("/modificar", methods=["GET", "POST"])
@login_required
def modificar():
    prod_id = request.values.get("prod_id", type=int)
    results = None
    if request.method == "POST" and request.form.get("accion") == "guardar":
        try:
            db.update_set(
                prod_id,
                request.form["set_name"].strip(),
                request.form.get("piece_count", type=int),
                request.form.get("theme_id", type=int),
                request.form.get("age_id", type=int),
                request.form.get("difficulty_id", type=int),
            )
            flash("Cambios guardados.", "ok")
        except Exception as e:
            flash(f"Error al modificar: {e}", "error")
    term = request.args.get("q", "")
    if term:
        results = db.search_sets(term)
    current = db.get_set(prod_id) if prod_id else None
    return render_template("modificar.html", themes=db.list_themes(),
                           ages=db.list_ages(), diffs=db.list_difficulties(),
                           results=results, term=term, current=current)


if __name__ == "__main__":
    app.run(debug=True)
