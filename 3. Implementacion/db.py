"""
db.py  ──  Capa MODELO (patrón MVC del documento de diseño).

Centraliza TODO el acceso a la base de datos. Se usa SQL crudo con
consultas parametrizadas (prepared statements) — NO se usa ORM — para que
las consultas exigidas por la rúbrica (JOIN, GROUP BY/HAVING, subconsulta)
queden visibles y evaluables, tal como decide el documento de diseño.

Regla de seguridad: los VALORES siempre van como parámetros (%s). Los
IDENTIFICADORES (nombres de tabla/columna) NO se pueden parametrizar en SQL,
así que cuando el usuario los elige se validan contra listas blancas.

Variables de entorno para la conexión MySQL:
    MYSQL_HOST      (default: 127.0.0.1)
    MYSQL_PORT      (default: 3306)
    MYSQL_USER      (default: legodb)
    MYSQL_PASSWORD  (default: "")
    MYSQL_DB        (default: legodb)
"""
import os
import mysql.connector

MYSQL_HOST     = os.environ.get("MYSQL_HOST",     "127.0.0.1")
MYSQL_PORT     = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER     = os.environ.get("MYSQL_USER",     "legodb")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DB       = os.environ.get("MYSQL_DB",       "legodb")


def get_conn():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset="utf8mb4",
        use_unicode=True,
    )


def q(sql, params=()):
    """Ejecuta un SELECT y devuelve (columnas, filas)."""
    con = get_conn()
    try:
        cur = con.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = list(cur.column_names)
        return cols, rows
    finally:
        con.close()


def execute(sql, params=()):
    """Ejecuta INSERT/UPDATE/DELETE y hace commit. Devuelve lastrowid."""
    con = get_conn()
    try:
        cur = con.cursor()
        cur.execute(sql, params)
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


# ---------- Catálogos para poblar formularios y selects ---------------------
def list_themes():
    return q("SELECT theme_id, theme_name FROM theme ORDER BY theme_name")[1]


def list_ages():
    return q("SELECT age_id, ages FROM age_range ORDER BY min_age")[1]


def list_difficulties():
    return q("SELECT difficulty_id, review_difficulty FROM difficulty "
             "ORDER BY difficulty_id")[1]


def list_countries():
    return q("SELECT country_code, country_name FROM country "
             "ORDER BY country_name")[1]


# ====================================================================== #
#  RF-04  ── Mostrar todas las tablas de la base de datos                 #
# ====================================================================== #
def all_tables():
    return q("""SELECT table_name AS name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name""")[1]


# ====================================================================== #
#  RF-05  ── Escoger un atributo de una relación (proyección)             #
#            Listas blancas para evitar inyección por identificador.      #
# ====================================================================== #
PROJECTABLE = {
    "lego_set":       ["prod_id", "set_name", "piece_count"],
    "theme":          ["theme_name", "theme_type"],
    "age_range":      ["ages", "min_age", "max_age"],
    "difficulty":     ["review_difficulty"],
    "country":        ["country_code", "country_name"],
    "review_summary": ["star_rating", "num_reviews", "play_star_rating",
                       "val_star_rating"],
}


def project_attribute(table, column, limit=200):
    if table not in PROJECTABLE or column not in PROJECTABLE[table]:
        raise ValueError("Tabla o columna no permitida")
    # identificadores ya validados contra lista blanca; el límite va parametrizado
    sql = (f"SELECT DISTINCT {column} FROM {table} "
           f"WHERE {column} IS NOT NULL ORDER BY {column} LIMIT %s")
    return q(sql, (limit,))


# ====================================================================== #
#  RF-06  ── JOIN de 3+ tablas                                           #
# ====================================================================== #
def join_sets(theme_id=None, limit=100):
    sql = """
        SELECT s.prod_id, s.set_name, t.theme_name, d.review_difficulty,
               a.ages, s.piece_count
        FROM lego_set s
        JOIN theme      t ON t.theme_id      = s.theme_id
        JOIN age_range  a ON a.age_id        = s.age_id
        LEFT JOIN difficulty d ON d.difficulty_id = s.difficulty_id
    """
    params = []
    if theme_id:
        sql += " WHERE s.theme_id = %s"
        params.append(theme_id)
    sql += " ORDER BY s.piece_count DESC LIMIT %s"
    params.append(limit)
    return q(sql, tuple(params))


# ====================================================================== #
#  RF-07  ── Agregación con GROUP BY / HAVING                            #
# ====================================================================== #
def avg_price_by_theme(country_code="US", min_sets=10):
    sql = """
        SELECT t.theme_name,
               COUNT(*)                   AS num_sets,
               ROUND(AVG(p.list_price),2) AS precio_promedio,
               ROUND(MIN(p.list_price),2) AS precio_min,
               ROUND(MAX(p.list_price),2) AS precio_max
        FROM price_listing p
        JOIN lego_set s ON s.prod_id  = p.prod_id
        JOIN theme    t ON t.theme_id = s.theme_id
        WHERE p.country_code = %s
        GROUP BY t.theme_name
        HAVING COUNT(*) >= %s
        ORDER BY precio_promedio DESC
    """
    return q(sql, (country_code, min_sets))


# ====================================================================== #
#  RF-03  ── Subconsulta (con WITH / CTE)                                #
# ====================================================================== #
def sets_above_avg_price(country_code="US", limit=100):
    sql = """
        WITH promedio AS (
            SELECT AVG(list_price) AS precio_medio
            FROM price_listing WHERE country_code = %s
        )
        SELECT s.set_name, t.theme_name, p.list_price
        FROM price_listing p
        JOIN lego_set s ON s.prod_id  = p.prod_id
        JOIN theme    t ON t.theme_id = s.theme_id
        WHERE p.country_code = %s
          AND p.list_price > (SELECT precio_medio FROM promedio)
        ORDER BY p.list_price DESC
        LIMIT %s
    """
    return q(sql, (country_code, country_code, limit))


# ====================================================================== #
#  RF-08 / RF-09  ── Insertar y modificar datos                          #
# ====================================================================== #
def insert_set(set_name, piece_count, theme_id, age_id, difficulty_id):
    # prod_id no tiene AUTO_INCREMENT en el esquema (los IDs vienen del CSV).
    # Se genera el siguiente ID disponible como MAX(prod_id) + 1.
    _, rows = q("SELECT COALESCE(MAX(prod_id), 0) + 1 AS next_id FROM lego_set")
    next_id = rows[0]["next_id"]

    execute(
        """INSERT INTO lego_set(prod_id, set_name, piece_count, theme_id, age_id, difficulty_id)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (next_id, set_name, piece_count, theme_id, age_id,
         difficulty_id if difficulty_id else None),
    )
    return next_id


def get_set(prod_id):
    cols, rows = q("SELECT * FROM lego_set WHERE prod_id = %s", (prod_id,))
    return rows[0] if rows else None


def search_sets(term, limit=25):
    return q("""SELECT prod_id, set_name, piece_count FROM lego_set
                WHERE set_name LIKE %s ORDER BY set_name LIMIT %s""",
             (f"%{term}%", limit))[1]


def update_set(prod_id, set_name, piece_count, theme_id, age_id, difficulty_id):
    execute(
        """UPDATE lego_set
           SET set_name=%s, piece_count=%s, theme_id=%s, age_id=%s, difficulty_id=%s
           WHERE prod_id=%s""",
        (set_name, piece_count, theme_id, age_id,
         difficulty_id if difficulty_id else None, prod_id),
    )


# ---------- Usuarios (RF-01, RF-02) ----------------------------------------
def get_user_by_name(username):
    cols, rows = q("SELECT * FROM app_user WHERE username = %s", (username,))
    return rows[0] if rows else None


def get_user_by_id(user_id):
    cols, rows = q("SELECT * FROM app_user WHERE user_id = %s", (user_id,))
    return rows[0] if rows else None


def create_user(username, password_hash):
    return execute(
        "INSERT INTO app_user(username, password_hash) VALUES (%s, %s)",
        (username, password_hash),
    )
