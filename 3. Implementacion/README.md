# 3. Implementación

Fase de **Implementación** del proyecto LegoDB (COMP4018-030), construida sobre
el diseño aprobado en la fase anterior. La aplicación es una interfaz web Flask
(patrón **MVC**) sobre una base de datos **SQLite** normalizada a 3NF/BCNF,
generada a partir de `lego_sets.csv`.

## Estructura

```
3. Implementación/
├── etl.py            # CSV  ->  lego.db (SQLite) + schema.sql   [conversión de datos]
├── schema.sql        # DDL del esquema (9 tablas + herencia + índices)
├── lego_dump.sql     # Volcado SQL completo (esquema + datos)
├── lego.db           # Base de datos lista para usar (se regenera con etl.py)
├── db.py             # MODELO  – acceso a datos con SQL crudo parametrizado
├── app.py            # CONTROLADOR – rutas Flask + autenticación (Flask-Login)
├── templates/        # VISTA   – plantillas Jinja2 (base + una por RF)
├── static/style.css  # estilos
├── requirements.txt  # dependencias
└── lego_sets.csv     # dataset de origen
```

## Cómo ejecutar

```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python etl.py        # genera lego.db (una sola vez; usa lego_sets.csv del directorio)
python app.py        # http://127.0.0.1:5000
```

Primero crea una cuenta en `/register` y luego inicia sesión.

## Modelo de datos (de la sábana al esquema normalizado)

El análisis del CSV mostró que el grano real es el par **(set, país)**: hay
**744 sets** repetidos en **21 países**. A partir de eso:

| # | Entidad          | Origen / nota |
|---|------------------|---------------|
| 1 | `lego_set`       | un registro por `prod_id` |
| 2 | `theme`          | superclase; `theme_type` discrimina la herencia |
| 3 | `licensed_theme` | subclase ISA THEME (IP externa); atributo `licensor` |
| 4 | `original_theme` | subclase ISA THEME (tema propio de LEGO) |
| 5 | `age_range`      | columna `ages` (100% constante por set) |
| 6 | `difficulty`     | columna `review_difficulty` |
| 7 | `country`        | 21 mercados |
| 8 | `price_listing`  | entidad asociativa SET–COUNTRY; atributo `list_price` |
| 9 | `review_summary` | ratings/num_reviews, 1:1 con el set |

La especialización THEME → {LICENSED, ORIGINAL} es **total y disjunta**.
`list_price` se modela como atributo de la relación M:N porque es lo único que
varía de verdad por país (los 744 sets tienen precios distintos entre mercados).

## Mapeo de requisitos funcionales

| RF | Descripción | Ruta | Dónde está la consulta |
|----|-------------|------|------------------------|
| RF-01 | Crear cuenta | `/register` | `db.create_user` (hash con Werkzeug) |
| RF-02 | Autenticar | `/login` | Flask-Login; rutas protegidas con `@login_required` |
| RF-03 | Subconsulta (WITH) | `/subconsulta` | `db.sets_above_avg_price` |
| RF-04 | Mostrar todas las tablas | `/tablas` | `db.all_tables` (`sqlite_master`) |
| RF-05 | Escoger un atributo | `/atributo` | `db.project_attribute` (lista blanca) |
| RF-06 | JOIN de 3+ tablas | `/join` | `db.join_sets` (set ⋈ theme ⋈ age ⋈ difficulty) |
| RF-07 | Agregación GROUP BY/HAVING | `/agregacion` | `db.avg_price_by_theme` |
| RF-08 | Insertar datos | `/insertar` | `db.insert_set` |
| RF-09 | Modificar datos | `/modificar` | `db.update_set` |

## Notas de diseño respetadas

- **Sin ORM**: todo el acceso a datos es SQL crudo con *prepared statements*
  (parámetros `?`), nunca concatenación de cadenas, según el documento de diseño.
- **MVC**: Modelo (`db.py`) / Vista (`templates/`) / Controlador (`app.py`).
- **Software libre** en todo el stack (Python, Flask, Jinja2, SQLite, Gunicorn).

## Diferencia con el documento de diseño: SQLite en vez de MySQL

El documento de diseño especifica **MySQL** con `mysql-connector-python`. Esta
implementación usa **SQLite** porque (a) el objetivo del proyecto pide un archivo
`.db`, y (b) corre sin levantar un servidor de base de datos, lo que la hace
portátil para la entrega. El estilo de SQL crudo parametrizado es idéntico, así
que migrar a MySQL solo afecta la función de conexión en `db.py` y unos pocos
tipos (`AUTOINCREMENT` → `AUTO_INCREMENT`, etc.).
