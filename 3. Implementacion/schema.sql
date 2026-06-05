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
    max_age INT,                          -- NULL si es abierto (p.ej. 6+)
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
    difficulty_id  INT,              -- NULL permitido (sets sin reseñas)
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
--     atributo de relación: list_price
CREATE TABLE price_listing (
    prod_id      INT    NOT NULL,
    country_code CHAR(2) NOT NULL,
    list_price   DOUBLE NOT NULL,
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
