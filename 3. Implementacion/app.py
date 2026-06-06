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
import os
import re

from flask import (Flask, render_template, request, redirect, url_for, flash)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

import db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")

csrf = CSRFProtect(app)   # protección CSRF global para todos los formularios POST


# ── Jinja2 filter: limpia símbolos de marca y corrige encoding ──────────────
_STRIP_SYMBOLS = str.maketrans("", "", "™®©")

# Tabla de normalización: comillas tipográficas y guiones largos → ASCII
_NORMALIZE = str.maketrans({
    "‘": "'",   # ' comilla simple izquierda
    "’": "'",   # ' comilla simple derecha / apóstrofe tipográfico
    "“": '"',   # " comilla doble izquierda
    "”": '"',   # " comilla doble derecha
    "–": "-",   # – guion medio
    "—": "-",   # — guion largo
    "…": "...", # … puntos suspensivos
})


def clean_text(value):
    """
    Limpia una cadena de texto para presentación en la interfaz:
      1. Intenta reparar mojibake UTF-8-como-Latin-1 (causa de España → EspaÃ±a,
         ½ → Â½, etc.) usando el truco encode/decode estándar.
      2. Elimina los símbolos ™ ® ©.
      3. Normaliza comillas tipográficas y guiones largos a ASCII.
    Valores no-string se devuelven sin cambio; None → '—'.
    """
    if value is None:
        return "—"
    if not isinstance(value, str):
        return value

    # Reparar mojibake: bytes UTF-8 mal interpretados como Latin-1
    # Ejemplo: 'EspaÃ±a' → encode latin-1 → b'\xc3\xb1' → decode utf-8 → 'ñ'
    try:
        value = value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass  # la cadena ya es Unicode correcto o tiene otro origen

    # Eliminar símbolos de marca registrada / derechos de autor
    value = value.translate(_STRIP_SYMBOLS)

    # Normalizar tipografía
    value = value.translate(_NORMALIZE)

    return value.strip()


app.jinja_env.filters["clean"] = clean_text

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


# ====================================================================== #
#  Validación de formulario de set (RF-08 / RF-09)                       #
#  Devuelve lista de mensajes de error; vacía = datos válidos.           #
# ====================================================================== #
def _validate_set_form(form, themes, ages, diffs):
    errors = []

    # 1. Nombre — obligatorio, máximo 300 caracteres
    name = form.get("set_name", "").strip()
    if not name:
        errors.append("El nombre del set es obligatorio.")
    elif len(name) > 300:
        errors.append(f"El nombre no puede superar 300 caracteres (actual: {len(name)}).")

    # 2. Cantidad de piezas — opcional; si se ingresa debe ser entero ≥ 1
    piece_raw = form.get("piece_count", "").strip()
    if piece_raw:
        try:
            piece_val = int(piece_raw)
            if piece_val < 1:
                errors.append("La cantidad de piezas debe ser un número positivo (mínimo 1).")
        except ValueError:
            errors.append("La cantidad de piezas debe ser un número entero (sin decimales).")

    # 3. Tema — obligatorio; debe ser un ID existente en la tabla theme
    valid_theme_ids = {str(t["theme_id"]) for t in themes}
    theme_raw = form.get("theme_id", "").strip()
    if not theme_raw:
        errors.append("Debes seleccionar un tema.")
    elif theme_raw not in valid_theme_ids:
        errors.append("El tema seleccionado no existe en la base de datos.")

    # 4. Rango de edad — obligatorio; debe ser un ID existente en age_range
    valid_age_ids = {str(a["age_id"]) for a in ages}
    age_raw = form.get("age_id", "").strip()
    if not age_raw:
        errors.append("Debes seleccionar un rango de edad.")
    elif age_raw not in valid_age_ids:
        errors.append("El rango de edad seleccionado no existe en la base de datos.")

    # 5. Dificultad: opcional; si se selecciona debe ser un ID valido
    diff_raw = form.get("difficulty_id", "").strip()
    if diff_raw:
        valid_diff_ids = {str(d["difficulty_id"]) for d in diffs}
        diff_ok = diff_raw in valid_diff_ids
        if not diff_ok:
            errors.append("La dificultad seleccionada no existe en la base de datos.")

    return errors


# ---------- RF-08: insertar -------------------------------------------------
@app.route("/insertar", methods=["GET", "POST"])
@login_required
def insertar():
    themes = db.list_themes()
    ages   = db.list_ages()
    diffs  = db.list_difficulties()

    if request.method == "POST":
        errors = _validate_set_form(request.form, themes, ages, diffs)
        if errors:
            for msg in errors:
                flash(msg, "error")
            # Re-render con los valores que el usuario ya escribió
            return render_template("insertar.html", themes=themes, ages=ages,
                                   diffs=diffs, form_data=request.form)
        try:
            new_id = db.insert_set(
                request.form["set_name"].strip(),
                request.form.get("piece_count", type=int),
                request.form.get("theme_id", type=int),
                request.form.get("age_id", type=int),
                request.form.get("difficulty_id", type=int),
            )
            flash(f"Set insertado correctamente con ID = {new_id}.", "ok")
            return redirect(url_for("modificar", prod_id=new_id))
        except Exception as e:
            flash(f"Error inesperado al insertar: {e}", "error")

    return render_template("insertar.html", themes=themes, ages=ages,
                           diffs=diffs, form_data=None)


# ---------- RF-09: modificar ------------------------------------------------
@app.route("/modificar", methods=["GET", "POST"])
@login_required
def modificar():
    themes = db.list_themes()
    ages   = db.list_ages()
    diffs  = db.list_difficulties()

    prod_id  = request.values.get("prod_id", type=int)
    results  = None
    form_data = None  # datos enviados por el usuario (solo cuando hay errores)

    if request.method == "POST" and request.form.get("accion") == "guardar":
        errors = _validate_set_form(request.form, themes, ages, diffs)

        # Validación adicional: el set a editar debe existir
        if prod_id is None:
            errors.append("No se especificó un set para modificar.")
        elif not db.get_set(prod_id):
            errors.append(f"No existe ningún set con ID = {prod_id}.")

        if errors:
            for msg in errors:
                flash(msg, "error")
            form_data = request.form  # conservar ediciones del usuario
        else:
            try:
                db.update_set(
                    prod_id,
                    request.form["set_name"].strip(),
                    request.form.get("piece_count", type=int),
                    request.form.get("theme_id", type=int),
                    request.form.get("age_id", type=int),
                    request.form.get("difficulty_id", type=int),
                )
                flash("Cambios guardados correctamente.", "ok")
            except Exception as e:
                flash(f"Error inesperado al modificar: {e}", "error")

    term = request.args.get("q", "")
    if term:
        results = db.search_sets(term)
    current = db.get_set(prod_id) if prod_id else None
    return render_template("modificar.html", themes=themes, ages=ages,
                           diffs=diffs, results=results, term=term,
                           current=current, form_data=form_data)


if __name__ == "__main__":
    app.run(debug=True)
