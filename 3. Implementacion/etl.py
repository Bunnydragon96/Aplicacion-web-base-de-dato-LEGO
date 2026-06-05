"""
etl.py  ──  Conversión lego_sets.csv  ->  MySQL (legodb) + schema.sql

Fase de Implementación del proyecto LegoDB (COMP4018-030).

Toma la "sábana" lego_sets.csv (12,261 filas, grano = set x país) y la
descompone en un esquema relacional normalizado (3NF/BCNF) con 9 conjuntos
de entidades y la jerarquía de herencia THEME -> {LICENSED_THEME, ORIGINAL_THEME}.

Decisiones de modelado derivadas del análisis de datos:
  - prod_id no es único entre filas: hay 744 sets, cada uno repetido por país.
    El grano real de la sábana es el par (prod_id, country).
  - list_price es lo único que varía de verdad por país (los 744 sets varían)
    -> se modela como atributo de la relación M:N SET–COUNTRY (price_listing).
  - ages es 100% constante por set -> atributo del SET (vía AGE_RANGE).
  - review_difficulty y los ratings son del SET (la variación entre países es
    ruido de datos); se consolidan tomando el valor más frecuente por set.

Variables de entorno para la conexión MySQL:
    MYSQL_HOST      (default: 127.0.0.1)
    MYSQL_PORT      (default: 3306)
    MYSQL_USER      (default: legodb)
    MYSQL_PASSWORD  (default: "")
    MYSQL_DB        (default: legodb)

Uso:  python etl.py
Salida: base de datos MySQL 'legodb' cargada y schema.sql actualizado.
"""

import os
import re
import pandas as pd
import mysql.connector
from collections import Counter

CSV_PATH   = os.environ.get("LEGO_CSV",        "lego_sets.csv")
SCHEMA_PATH = "schema.sql"

MYSQL_HOST     = os.environ.get("MYSQL_HOST",     "127.0.0.1")
MYSQL_PORT     = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER     = os.environ.get("MYSQL_USER",     "legodb")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DB       = os.environ.get("MYSQL_DB",       "legodb")

# --------------------------------------------------------------------------- #
# 1. Clasificación de los 40 temas: LICENSED (IP externa) vs ORIGINAL (LEGO)   #
#    Editable: si el profesor discrepa de alguna, se cambia aquí y se re-corre #
# --------------------------------------------------------------------------- #
LICENSED = {
    "Star Wars™": "Lucasfilm / Disney",
    "Marvel Super Heroes": "Marvel / Disney",
    "THE LEGO® BATMAN MOVIE": "DC / Warner Bros.",
    "Minecraft™": "Mojang / Microsoft",
    "Disney™": "The Walt Disney Company",
    "DC Comics™ Super Heroes": "DC / Warner Bros.",
    "Speed Champions": "Fabricantes de autos (Ferrari, Porsche, etc.)",
    "DC Super Hero Girls": "DC / Warner Bros.",
    "Angry Birds™": "Rovio",
    "Ghostbusters™": "Sony / Columbia",
    "Blue's Helicopter Pursuit": "Jurassic World / Universal",
    "Carnotaurus Gyrosphere Escape": "Jurassic World / Universal",
    "Jurassic Park Velociraptor Chase": "Jurassic Park / Universal",
    "Dilophosaurus Outpost Attack": "Jurassic World / Universal",
    "Indoraptor Rampage at Lockwood Estate": "Jurassic World / Universal",
    "Pteranodon Chase": "Jurassic World / Universal",
    "Stygimoloch Breakout": "Jurassic World / Universal",
    "T. rex Transport": "Jurassic World / Universal",
}
# Todo lo que no esté en LICENSED se considera ORIGINAL (tema propio de LEGO).

COUNTRY_NAMES = {
    "AT": "Austria", "AU": "Australia", "BE": "Bélgica", "CA": "Canadá",
    "CH": "Suiza", "CZ": "Chequia", "DE": "Alemania", "DN": "Dinamarca",
    "ES": "España", "FI": "Finlandia", "FR": "Francia", "GB": "Reino Unido",
    "IE": "Irlanda", "IT": "Italia", "LU": "Luxemburgo", "NL": "Países Bajos",
    "NO": "Noruega", "NZ": "Nueva Zelanda", "PL": "Polonia", "PT": "Portugal",
    "US": "Estados Unidos",
}


def parse_ages(ages):
    """ '6-12'->(6,12), '6+'->(6,None), '4-99'->(4,99), '1½-3'->(1,3) """
    s = ages.replace("½", "")  # 1½ -> 1 (piso)
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d+)\s*\+$", s)
    if m:
        return int(m.group(1)), None
    m = re.match(r"^(\d+)$", s)
    if m:
        return int(m.group(1)), int(m.group(1))
    return None, None


def mode_or_first(series):
    """Valor más frecuente no nulo (consolida ruido entre países)."""
    vals = series.dropna().tolist()
    if not vals:
        return None
    return Counter(vals).most_common(1)[0][0]


SCHEMA_SQL = """\
-- ========================================================================
-- LegoDB - Esquema relacional normalizado (3NF/BCNF)  [MySQL 8+]
-- 9 entidades, herencia THEME -> {LICENSED_THEME, ORIGINAL_THEME}
-- Generado por etl.py
-- ========================================================================

CREATE DATABASE IF NOT EXISTS legodb
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE legodb;

-- (1) AGE_RANGE  -- rango de edad recomendado
CREATE TABLE age_range (
    age_id  INT          NOT NULL AUTO_INCREMENT,
    ages    VARCHAR(20)  NOT NULL,
    min_age INT,
    max_age INT,
    PRIMARY KEY (age_id),
    UNIQUE KEY uq_ages (ages)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (2) DIFFICULTY  -- dificultad de armado
CREATE TABLE difficulty (
    difficulty_id     INT          NOT NULL AUTO_INCREMENT,
    review_difficulty VARCHAR(100) NOT NULL,
    PRIMARY KEY (difficulty_id),
    UNIQUE KEY uq_difficulty (review_difficulty)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (3) THEME  -- superclase; theme_type es el discriminante de la especialización
CREATE TABLE theme (
    theme_id   INT          NOT NULL AUTO_INCREMENT,
    theme_name VARCHAR(200) NOT NULL,
    theme_type ENUM('LICENSED','ORIGINAL') NOT NULL,
    PRIMARY KEY (theme_id),
    UNIQUE KEY uq_theme_name (theme_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (4) LICENSED_THEME  -- subclase ISA THEME (especialización total y disjunta)
CREATE TABLE licensed_theme (
    theme_id INT          NOT NULL,
    licensor VARCHAR(200),
    PRIMARY KEY (theme_id),
    FOREIGN KEY (theme_id) REFERENCES theme(theme_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (5) ORIGINAL_THEME  -- subclase ISA THEME
CREATE TABLE original_theme (
    theme_id INT NOT NULL,
    PRIMARY KEY (theme_id),
    FOREIGN KEY (theme_id) REFERENCES theme(theme_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (6) LEGO_SET  -- entidad central
CREATE TABLE lego_set (
    prod_id        INT          NOT NULL,
    set_name       VARCHAR(300) NOT NULL,
    piece_count    INT,
    prod_desc      TEXT,
    prod_long_desc TEXT,
    age_id         INT          NOT NULL,
    difficulty_id  INT,
    theme_id       INT          NOT NULL,
    PRIMARY KEY (prod_id),
    FOREIGN KEY (age_id)        REFERENCES age_range(age_id),
    FOREIGN KEY (difficulty_id) REFERENCES difficulty(difficulty_id),
    FOREIGN KEY (theme_id)      REFERENCES theme(theme_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (7) COUNTRY  -- país/mercado
CREATE TABLE country (
    country_code CHAR(2)      NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (country_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (8) PRICE_LISTING  -- entidad asociativa: resuelve M:N SET–COUNTRY
CREATE TABLE price_listing (
    prod_id      INT     NOT NULL,
    country_code CHAR(2) NOT NULL,
    list_price   DOUBLE  NOT NULL,
    PRIMARY KEY (prod_id, country_code),
    FOREIGN KEY (prod_id)      REFERENCES lego_set(prod_id),
    FOREIGN KEY (country_code) REFERENCES country(country_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- (9) REVIEW_SUMMARY  -- resumen de reseñas, 1:1 con LEGO_SET
CREATE TABLE review_summary (
    prod_id          INT    NOT NULL,
    num_reviews      INT,
    star_rating      DOUBLE,
    play_star_rating DOUBLE,
    val_star_rating  DOUBLE,
    PRIMARY KEY (prod_id),
    FOREIGN KEY (prod_id) REFERENCES lego_set(prod_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Usuarios de la aplicación (RF-01, RF-02). Contraseñas con hash (Werkzeug).
CREATE TABLE app_user (
    user_id       INT          NOT NULL AUTO_INCREMENT,
    username      VARCHAR(150) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Índices de apoyo para los JOIN/agregaciones de la interfaz
CREATE INDEX idx_set_theme      ON lego_set(theme_id);
CREATE INDEX idx_set_age        ON lego_set(age_id);
CREATE INDEX idx_set_difficulty ON lego_set(difficulty_id);
CREATE INDEX idx_price_country  ON price_listing(country_code);
"""

# Tablas en orden de dependencia (para DROP respetando FK)
_TABLES_DROP_ORDER = [
    "review_summary", "price_listing", "lego_set",
    "licensed_theme", "original_theme", "theme",
    "age_range", "difficulty", "country", "app_user",
]


def _exec_schema(con):
    """Ejecuta el DDL tabla a tabla sobre la conexión ya establecida."""
    cur = con.cursor()
    # Eliminar tablas existentes en orden inverso a las FK
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for tbl in _TABLES_DROP_ORDER:
        cur.execute(f"DROP TABLE IF EXISTS `{tbl}`")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")

    # Ejecutar sólo los CREATE TABLE / CREATE INDEX (saltar USE / CREATE DATABASE)
    for stmt in SCHEMA_SQL.split(";"):
        stmt = stmt.strip()
        if stmt and stmt.upper().startswith(("CREATE TABLE", "CREATE INDEX")):
            cur.execute(stmt)
    con.commit()
    cur.close()


def build():
    print(f"Leyendo {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH)
    df = df[df["theme_name"].notna()].copy()  # 3 filas sin tema
    print(f"  {len(df)} filas, {df['prod_id'].nunique()} sets, "
          f"{df['country'].nunique()} países")

    # Conectar a MySQL (la base de datos debe existir o se crea antes)
    con_root = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD,
        charset="utf8mb4",
    )
    con_root.cursor().execute(
        "CREATE DATABASE IF NOT EXISTS `legodb` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    con_root.commit()
    con_root.close()

    con = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DB, charset="utf8mb4",
    )
    _exec_schema(con)
    cur = con.cursor()

    # ---- AGE_RANGE ----
    ages = sorted(df["ages"].dropna().unique())
    age_id = {a: i + 1 for i, a in enumerate(ages)}
    for a, i in age_id.items():
        mn, mx = parse_ages(a)
        cur.execute(
            "INSERT INTO age_range(age_id, ages, min_age, max_age) VALUES (%s,%s,%s,%s)",
            (i, a, mn, mx),
        )

    # ---- DIFFICULTY ----
    diffs = sorted(df["review_difficulty"].dropna().unique())
    diff_id = {d: i + 1 for i, d in enumerate(diffs)}
    for d, i in diff_id.items():
        cur.execute(
            "INSERT INTO difficulty(difficulty_id, review_difficulty) VALUES (%s,%s)",
            (i, d),
        )

    # ---- THEME + subclases (herencia) ----
    themes = sorted(df["theme_name"].dropna().unique())
    theme_id = {t: i + 1 for i, t in enumerate(themes)}
    for t, i in theme_id.items():
        ttype = "LICENSED" if t in LICENSED else "ORIGINAL"
        cur.execute(
            "INSERT INTO theme(theme_id, theme_name, theme_type) VALUES (%s,%s,%s)",
            (i, t, ttype),
        )
        if ttype == "LICENSED":
            cur.execute(
                "INSERT INTO licensed_theme(theme_id, licensor) VALUES (%s,%s)",
                (i, LICENSED[t]),
            )
        else:
            cur.execute(
                "INSERT INTO original_theme(theme_id) VALUES (%s)", (i,)
            )

    # ---- COUNTRY ----
    for code in sorted(df["country"].dropna().unique()):
        cur.execute(
            "INSERT INTO country(country_code, country_name) VALUES (%s,%s)",
            (code, COUNTRY_NAMES.get(code, code)),
        )

    # ---- LEGO_SET + REVIEW_SUMMARY (consolidados por prod_id) ----
    for prod_id, g in df.groupby("prod_id"):
        set_name = mode_or_first(g["set_name"])
        piece    = mode_or_first(g["piece_count"])
        pdesc    = mode_or_first(g["prod_desc"])
        pldesc   = mode_or_first(g["prod_long_desc"])
        a        = mode_or_first(g["ages"])
        d        = mode_or_first(g["review_difficulty"])
        t        = mode_or_first(g["theme_name"])
        cur.execute(
            """INSERT INTO lego_set(prod_id, set_name, piece_count, prod_desc,
               prod_long_desc, age_id, difficulty_id, theme_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (int(prod_id), set_name,
             int(piece) if pd.notna(piece) else None,
             pdesc, pldesc, age_id[a],
             diff_id.get(d) if d else None,
             theme_id[t]),
        )
        nr = mode_or_first(g["num_reviews"])
        cur.execute(
            """INSERT INTO review_summary(prod_id, num_reviews, star_rating,
               play_star_rating, val_star_rating) VALUES (%s,%s,%s,%s,%s)""",
            (int(prod_id),
             int(nr) if pd.notna(nr) else None,
             mode_or_first(g["star_rating"]),
             mode_or_first(g["play_star_rating"]),
             mode_or_first(g["val_star_rating"])),
        )

    # ---- PRICE_LISTING (grano set x país) ----
    seen = set()
    for _, r in df.iterrows():
        key = (int(r["prod_id"]), r["country"])
        if key in seen:  # duplicados exactos set/país -> nos quedamos con el 1ro
            continue
        seen.add(key)
        cur.execute(
            "INSERT INTO price_listing(prod_id, country_code, list_price) VALUES (%s,%s,%s)",
            (int(r["prod_id"]), r["country"], float(r["list_price"])),
        )

    con.commit()

    # ---- Verificación ----
    print("\nConteos por tabla:")
    for tbl in ["age_range", "difficulty", "theme", "licensed_theme",
                "original_theme", "lego_set", "country", "price_listing",
                "review_summary"]:
        cur.execute(f"SELECT COUNT(*) FROM `{tbl}`")
        n = cur.fetchone()[0]
        print(f"  {tbl:16s} {n}")

    # Integridad referencial (MySQL no expone un PRAGMA equivalente, pero
    # los FK están activos durante el INSERT; si llegamos aquí sin error = OK)
    print("\nIntegridad referencial: OK (sin errores de FK durante la carga)")
    cur.close()
    con.close()

    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        f.write(SCHEMA_SQL)
    print(f"\nGenerado: schema.sql  |  Base de datos: {MYSQL_DB}@{MYSQL_HOST}")


if __name__ == "__main__":
    build()
