# Descomposición Formal: De la Sábana CSV al Esquema 3NF/BCNF

**Proyecto:** LegoDB — COMP4018-030  
**Fuente:** `lego_sets.csv` (12 261 filas, 14 columnas)

---

## 1. Tabla original (Forma No Normalizada — UNF)

El archivo CSV es una única "sábana" plana. Cada fila representa el par
**(set, país)**: el mismo set LEGO aparece repetido para cada uno de los
21 mercados en los que se vende, acumulando un total de 12 261 filas para
solo 744 sets distintos.

```
LEGO_CSV(ages, list_price, num_reviews, piece_count, play_star_rating,
         prod_desc, prod_id, prod_long_desc, review_difficulty,
         set_name, star_rating, theme_name, val_star_rating, country)
```

**Observaciones del análisis de datos:**

| Columna | Observación |
|---|---|
| `prod_id` | No es único entre filas; se repite por país |
| `country` | 21 valores distintos (AT, AU, BE, CA, CH, CZ, DE, DN, ES, FI, FR, GB, IE, IT, LU, NL, NO, NZ, PL, PT, US) |
| `list_price` | El CSV contiene 1 391 filas duplicadas en el par `(prod_id, country)`; el ETL las deduplica. El par resultante es único: 10 870 combinaciones distintas. Es el único atributo que varía genuinamente por mercado. |
| `ages` | 100 % constante por `prod_id` (0 variaciones en 744 sets) |
| `set_name` | Constante por `prod_id` con ruido menor en 6 sets (variantes tipográficas) |
| `piece_count` | Constante por `prod_id` con ruido menor en 2 sets |
| `theme_name` | 41 valores brutos en el CSV, pero 3 filas tienen tema vacío `''` (ruido); el ETL descarta esas filas vía `dropna()`. **40 temas reales** se cargan en la base de datos. Varía para 19 sets (ruido); se consolida con el valor más frecuente por `prod_id`. |
| `review_difficulty` | Varía para 8 sets (ruido); se consolida con el valor más frecuente |
| `star_rating`, `play_star_rating`, `val_star_rating`, `num_reviews` | Varían para ~20 sets (ruido); se consolidan por `prod_id` |
| `prod_desc`, `prod_long_desc` | Constantes por `prod_id` |

La **clave candidata** de la sábana es el par `{prod_id, country}`.

---

## 2. Primera Forma Normal (1NF)

**Requisito:** no hay grupos repetidos ni atributos multivaluados; existe una clave primaria.

La sábana ya cumple 1NF: cada celda contiene un solo valor atómico.
Se define la clave primaria compuesta:

```
PK = {prod_id, country}
```

**Tabla en 1NF:**
```
R1(prod_id*, country*, ages, list_price, num_reviews, piece_count,
   play_star_rating, prod_desc, prod_long_desc, review_difficulty,
   set_name, star_rating, theme_name, val_star_rating)
```

*(asterisco = parte de la clave primaria)*

---

## 3. Segunda Forma Normal (2NF)

**Requisito:** toda columna no clave depende de la clave **completa**, no de una
parte de ella.

Con la clave compuesta `{prod_id, country}`, se identifican las
**dependencias parciales**: atributos que dependen solo de `prod_id`
(no necesitan `country` para ser determinados).

### Dependencias funcionales identificadas

| Atributo(s) | Determinante | Tipo de dependencia |
|---|---|---|
| `list_price` | `{prod_id, country}` | Completa — permanece en tabla base |
| `set_name` | `prod_id` | **Parcial** — no depende de `country` |
| `piece_count` | `prod_id` | **Parcial** |
| `prod_desc` | `prod_id` | **Parcial** |
| `prod_long_desc` | `prod_id` | **Parcial** |
| `ages` | `prod_id` | **Parcial** |
| `theme_name` | `prod_id` | **Parcial** |
| `review_difficulty` | `prod_id` | **Parcial** |
| `star_rating` | `prod_id` | **Parcial** |
| `play_star_rating` | `prod_id` | **Parcial** |
| `val_star_rating` | `prod_id` | **Parcial** |
| `num_reviews` | `prod_id` | **Parcial** |

### Descomposición 1NF → 2NF

Se extraen los atributos con dependencia parcial a su propia tabla,
conservando en la tabla base solo `list_price` (el único atributo que
genuinamente depende del par completo):

```
SET_PAIS(prod_id*, country*, list_price)

SET_DATOS(prod_id*, set_name, piece_count, prod_desc, prod_long_desc,
          ages, theme_name, review_difficulty, star_rating,
          play_star_rating, val_star_rating, num_reviews)
```

La sábana queda libre de dependencias parciales. Ambas tablas están en 2NF.

---

## 4. Tercera Forma Normal (3NF)

**Requisito:** ninguna columna no clave depende transitivamente de la clave
primaria (es decir, ningún no-clave determina a otro no-clave).

Se analiza `SET_DATOS` en busca de **dependencias transitivas**:

### Dependencias transitivas en SET_DATOS

| Cadena transitiva | Descripción |
|---|---|
| `prod_id → ages → {min_age, max_age}` | `ages` es una etiqueta compuesta (ej. "6-12") de la que se pueden derivar `min_age` y `max_age`. `ages` funciona como clave de un catálogo propio. |
| `prod_id → review_difficulty → (descripción de nivel)` | `review_difficulty` es una etiqueta categórica que funciona como clave de un catálogo de dificultades. |
| `prod_id → theme_name → theme_type` | El tipo de tema (LICENSED / ORIGINAL) depende del nombre del tema, no directamente del set. |
| `prod_id → theme_name → licensor` | El licenciante (ej. "Lucasfilm / Disney") depende del tema, no del set. |

Adicionalmente, los atributos de reseña (`star_rating`, `num_reviews`, etc.)
forman un grupo cohesivo con dependencia directa de `prod_id`, pero
separados de los datos del set para reducir el ancho de la tabla y
permitir conjuntos vacíos (sets sin reseñas).

### Descomposición SET_DATOS → 3NF

Se eliminan las dependencias transitivas extrayendo cada catálogo a su
propia tabla:

```
AGE_RANGE(age_id*, ages, min_age, max_age)
    ages → {min_age, max_age}   [clave natural: ages]

DIFFICULTY(difficulty_id*, review_difficulty)
    clave natural: review_difficulty

THEME(theme_id*, theme_name, theme_type)
    theme_name → theme_type     [theme_type discrimina la herencia]

SET_DATOS2(prod_id*, set_name, piece_count, prod_desc, prod_long_desc,
           age_id FK→AGE_RANGE,
           difficulty_id FK→DIFFICULTY,
           theme_id FK→THEME)

REVIEW_SUMMARY(prod_id* FK→SET_DATOS2,
               num_reviews, star_rating, play_star_rating,
               val_star_rating)
```

La tabla `SET_PAIS` también se descompone para aislar el catálogo de países:

```
COUNTRY(country_code*, country_name)

PRICE_LISTING(prod_id* FK→SET_DATOS2, country_code* FK→COUNTRY, list_price)
```

Todas las tablas resultantes están en **3NF**: ningún atributo no clave
determina a otro atributo no clave dentro de la misma tabla.

---

## 5. Verificación BCNF

**Requisito BCNF:** para toda dependencia funcional `X → Y`, `X` debe ser
una superclave.

Se revisa cada tabla resultante:

| Tabla | Dependencias funcionales no triviales | ¿X es superclave? | ¿BCNF? |
|---|---|---|---|
| `AGE_RANGE` | `age_id → {ages, min_age, max_age}`; `ages → {age_id, min_age, max_age}` | Sí (ambas son claves candidatas) | ✓ |
| `DIFFICULTY` | `difficulty_id → review_difficulty`; `review_difficulty → difficulty_id` | Sí (ambas son claves candidatas) | ✓ |
| `THEME` | `theme_id → {theme_name, theme_type}`; `theme_name → {theme_id, theme_type}` | Sí (ambas son claves candidatas) | ✓ |
| `SET_DATOS2` | `prod_id → {set_name, piece_count, …, age_id, difficulty_id, theme_id}` | Sí (`prod_id` es PK) | ✓ |
| `REVIEW_SUMMARY` | `prod_id → {num_reviews, star_rating, …}` | Sí (`prod_id` es PK y FK 1:1) | ✓ |
| `COUNTRY` | `country_code → country_name`; `country_name → country_code` | Sí (ambas son claves candidatas) | ✓ |
| `PRICE_LISTING` | `{prod_id, country_code} → list_price` | Sí (PK compuesta) | ✓ |

Todas las tablas satisfacen BCNF.

---

## 6. Especialización ISA sobre THEME (herencia)

El análisis de los **40 temas reales** del dataset permite clasificarlos en dos
categorías mutuamente excluyentes:

- **LICENSED_THEME**: temas basados en propiedad intelectual externa (Star Wars, Marvel, Disney, Minecraft, etc.) — tienen un atributo adicional `licensor`.
- **ORIGINAL_THEME**: temas propios de LEGO (City, Technic, Creator, Classic, etc.) — sin atributo adicional.

Esta especialización es **total** (todo tema es Licensed u Original) y
**disjunta** (ningún tema puede ser ambos a la vez), verificado en la base de
datos: 18 temas LICENSED + 22 temas ORIGINAL = 40 total, con intersección vacía.
Se implementa con el patrón de tabla por subclase:

```
THEME(theme_id*, theme_name, theme_type ENUM('LICENSED','ORIGINAL'))

LICENSED_THEME(theme_id* FK→THEME, licensor)
    -- subclase ISA THEME

ORIGINAL_THEME(theme_id* FK→THEME)
    -- subclase ISA THEME
```

---

## 7. Esquema final normalizado (resumen)

El proceso completo desde la sábana CSV hasta el esquema 3NF/BCNF produce
**9 relaciones de datos** derivadas del CSV. La base de datos contiene además
una décima tabla de aplicación (`app_user`) que no proviene del CSV sino de
los requisitos funcionales de autenticación (RF-01, RF-02):

| # | Tabla | Clave primaria | Proviene de | Filas en DB |
|---|---|---|---|---|
| 1 | `age_range` | `age_id` | Eliminar transitiva: `prod_id → ages → {min_age, max_age}` | 31 |
| 2 | `difficulty` | `difficulty_id` | Eliminar transitiva: `prod_id → review_difficulty` | 5 |
| 3 | `theme` | `theme_id` | Eliminar transitiva: `prod_id → theme_name → theme_type` | 40 |
| 4 | `licensed_theme` | `theme_id` (FK) | Especialización ISA de `theme` | 18 |
| 5 | `original_theme` | `theme_id` (FK) | Especialización ISA de `theme` | 22 |
| 6 | `lego_set` | `prod_id` | `SET_DATOS2` — tabla central del set | 744 |
| 7 | `country` | `country_code` | Eliminar parcial: `country` en `SET_PAIS` | 21 |
| 8 | `price_listing` | `{prod_id, country_code}` | `SET_PAIS` tras extraer `country` | 10 868 |
| 9 | `review_summary` | `prod_id` (FK 1:1) | Separación de atributos de reseña | 744 |
| — | `app_user` | `user_id` | Requisito RF-01/RF-02 (autenticación) — no del CSV | variable |

**Reducción de redundancia:** la sábana original tenía 12 261 filas (de las cuales
1 391 son duplicados del par `(prod_id, country)`) con los datos del set repetidos
por cada mercado. Tras deduplicación y filtrado de 2 sets con tema vacío, el ETL
carga **10 868 filas en `price_listing`** (la única tabla donde la variación por
país es legítima). El resto de datos se almacena sin redundancia: 744 filas en
`lego_set`, 40 en `theme`, 21 en `country`, etc.

### Esquema relacional en notación estándar

```
age_range(age_id, ages, min_age, max_age)
difficulty(difficulty_id, review_difficulty)
theme(theme_id, theme_name, theme_type)
licensed_theme(theme_id → theme, licensor)
original_theme(theme_id → theme)
lego_set(prod_id, set_name, piece_count, prod_desc, prod_long_desc,
         age_id → age_range, difficulty_id → difficulty, theme_id → theme)
country(country_code, country_name)
price_listing(prod_id → lego_set, country_code → country, list_price)
review_summary(prod_id → lego_set, num_reviews, star_rating,
               play_star_rating, val_star_rating)

-- Tabla de aplicación (RF-01/RF-02); no derivada del CSV:
app_user(user_id, username, password_hash)
```

*(PK en negrita o primera posición; `→ tabla` = clave foránea)*
