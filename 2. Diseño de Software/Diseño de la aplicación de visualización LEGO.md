# Objetivos
Los objetivos de diseño de **LegoDB** se derivan directamente de los requisitos funcionales (RF-01 al RF-09) y no funcionales (RNF-01 al RNF-04) definidos durante la fase de Ingeniería de Requisitos, así como de las especificaciones impuestas por el cliente (profesor) en la rúbrica del proyecto. Estos objetivos sirven como criterio para justificar las decisiones tomadas en el diagrama E/R, el modelo relacional, la arquitectura de la aplicación web y la elección del patrón de diseño.

- **Garantizar la integridad y consistencia de los datos.** Dado que el insumo principal del sistema es el archivo `lego_sets.csv` —donde temas, subtemas y piezas vienen en una sola "sábana"—, el diseño debe descomponer esta estructura en al menos 8 entidades y 6 relaciones, normalizadas hasta 3NF (o BCNF cuando no se pierdan dependencias funcionales). Esto elimina redundancias, evita anomalías de inserción/modificación y asegura que las restricciones de integridad referencial se cumplan a nivel del DBMS.
- **Facilitar la mantenibilidad y escalabilidad mediante separación de responsabilidades.** El diseño adopta el patrón arquitectónico **Modelo–Vista–Controlador (MVC)** implementado sobre **Flask**, donde el Modelo encapsula el acceso a MySQL, las Vistas se renderizan mediante **plantillas Jinja2**, y los Controladores se materializan como funciones de ruta de Flask que orquestan las peticiones entre ambos. En la terminología propia de Flask este patrón se denomina MVT (Model–View–Template), pero la separación de responsabilidades es equivalente a un MVC clásico. Esta separación permite, por ejemplo, modificar una consulta SQL sin alterar la presentación, o cambiar las plantillas sin afectar la lógica de negocio.
- **Preservar el control directo sobre el lenguaje SQL.** El acceso a MySQL desde la capa Modelo se realiza mediante **SQL crudo con consultas parametrizadas**, en lugar de un ORM (Object-Relational Mapper) como SQLAlchemy. Esta decisión es deliberada y responde a dos motivaciones: (1) la rúbrica del proyecto evalúa explícitamente la calidad de las consultas SQL, exigiendo al menos un JOIN de tres o más tablas (RF-06), una consulta con agregación mediante `GROUP BY`/`HAVING` (RF-07) y una subconsulta con o sin `WITH` (RF-03); un ORM ocultaría estas consultas detrás de su propia API, dificultando demostrar el dominio del lenguaje que el curso busca evaluar; (2) el contacto directo con SQL refuerza la transparencia del diseño y permite optimizar consultas a nivel de la base de datos cuando sea necesario.
- **Asegurar la usabilidad para el usuario final.** Aunque el público objetivo son personas familiarizadas con bases de datos (según el alcance definido), la interfaz debe ser intuitiva y, donde no lo sea, proveer instrucciones (RNF-04). Las plantillas Jinja2 correspondientes a los RF de visualización de consultas (RF-03 a RF-07) y de manipulación de datos (RF-08, RF-09) se diseñan siguiendo principios de **diseño centrado en el usuario**, presentando los resultados en formato tabular y formularios con validación visible. Una plantilla base (`base.html`) heredada por todas las vistas garantiza consistencia visual y de navegación.
- **Cumplir con los requisitos de seguridad y confiabilidad.** El diseño incluye un módulo de autenticación (RF-01, RF-02) que actúa como punto de control único antes de exponer cualquier funcionalidad de consulta o modificación, gestionado mediante **Flask-Login**. Las contraseñas se almacenan con _hashing_ seguro provisto por **Werkzeug** (nunca en texto plano), y todas las consultas SQL —pese a ser crudas— utilizan **parámetros enlazados (_prepared statements_)** para mitigar el riesgo de inyección SQL. La concatenación de cadenas para construir consultas queda explícitamente prohibida en el diseño de la capa Modelo.
- **Promover la modularidad y la reutilización de componentes.** Cada requisito funcional de visualización (RF-03 al RF-07) se implementa como un controlador independiente con su plantilla Jinja2 asociada, reutilizando un mismo componente de renderizado de tablas y un mismo módulo de conexión a la base de datos. Esto reduce duplicación de código y se alinea con el modelo cascada **con reutilización** adoptado en el README.
- **Asegurar la accesibilidad y portabilidad de la aplicación.** El diseño contempla el despliegue en una máquina virtual con dominio propio (RNF-01, RNF-02) usando exclusivamente herramientas de software libre: Python, Flask, Jinja2, MySQL y Gunicorn. Esto garantiza que la aplicación sea accesible desde los principales navegadores web (RNF-03) sin dependencias propietarias y cumple con la limitación del proyecto de usar únicamente software libre.

# Descripción de métodos, técnicas, herramientas y/o notaciones de diseño

Para alcanzar los objetivos anteriores se emplea la siguiente combinación de métodos, técnicas, herramientas y notaciones, seleccionados por su compatibilidad con el modelo cascada con reutilización, la restricción de software libre y los entregables exigidos en la rúbrica.

**Métodos de diseño**

- **Diseño orientado a datos.** Es el método rector del proyecto: la estructura de la base de datos se diseña primero a partir del análisis de `lego_sets.csv`, y la aplicación web se construye sobre ese modelo ya estable y aprobado por el cliente. Esto refleja la dependencia explícita entre la fase de modelado de datos y la de implementación.
- **Diseño basado en componentes y patrón arquitectónico MVC** sobre Flask. Cada requisito funcional se materializa como un par Controlador–Plantilla que opera sobre un Modelo común de acceso a MySQL.
- **Diseño centrado en el usuario.** Las plantillas y los flujos de interacción (login, listado de consultas, formularios de inserción y modificación) se diseñan a partir de los casos de uso documentados en `Especificacion_Requisitos_Funcionales.md`.

**Técnicas**

- **Modelado entidad-relación (E/R)** para capturar las 8 o más entidades y 6 o más relaciones, incluyendo la jerarquía de herencia exigida por el cliente, especificando si es total o parcial y disjunta o solapada.
- **Traducción al modelo relacional** con identificación de claves primarias, claves foráneas y restricciones de integridad referencial.
- **Análisis de dependencias funcionales y normalización progresiva** hasta 3NF, escalando a BCNF cuando la descomposición no provoque pérdida de dependencias funcionales.
- **Aplicación del patrón arquitectónico MVC** como técnica de organización del código de la aplicación Flask, estableciendo fronteras claras entre acceso a datos, lógica de control y presentación.
- **Modelado de casos de uso** para vincular cada requisito funcional con su flujo de interacción correspondiente, ya iniciado en la fase de requisitos con los diagramas `diagrama_caso_uso_RF01..09`.
- **Uso obligatorio de consultas parametrizadas (_prepared statements_)** en toda la capa Modelo, como técnica de defensa contra inyección SQL. Dado que se trabaja con SQL crudo, esta técnica es crítica y queda registrada como restricción de diseño: la concatenación de cadenas para construir consultas queda prohibida.
- **Centralización del acceso a datos en un módulo único** que expone funciones de consulta y conexión, evitando que los controladores manipulen directamente el driver de MySQL. Esto facilita el mantenimiento y la auditoría de las consultas.

**Herramientas**

_Diseño y modelado_

- **Draw.io / Lucidchart** para los diagramas E/R, de casos de uso y de arquitectura. Se eligen por ser de uso libre y por la familiaridad ya establecida con Lucidchart desde la fase de requisitos.
- **MySQL Workbench** para refinar el modelo relacional, generar el script DDL inicial a partir del diagrama E/R y administrar la base de datos durante el desarrollo (sustituye a phpMyAdmin en este stack).

_Implementación_

- **Python 3** como lenguaje de la aplicación, manteniendo la práctica del lenguaje.
- **Flask** como microframework web. Se elige sobre alternativas como Django por su tamaño reducido, su curva de aprendizaje suave y porque deja al desarrollador definir explícitamente la estructura MVC, lo cual es valioso en un contexto académico.
- **Jinja2** como motor de plantillas (incluido por defecto en Flask) para implementar la capa de Vista, con herencia de plantillas a partir de un `base.html` para mantener consistencia visual entre las páginas de los RF-03 al RF-09.
- **MySQL** como DBMS, alineado con el requisito del profesor.
- **mysql-connector-python** como driver oficial de MySQL para Python en la capa Modelo. Toda la interacción con la base de datos se realiza mediante SQL crudo escrito a mano en cumplimiento con la decisión de diseño documentada en los Objetivos.
- **Flask-Login** para la gestión de sesiones de usuario (RF-02), y **Werkzeug** (incluido con Flask) para el _hashing_ seguro de contraseñas en RF-01.
- **pip** y **venv** para la gestión de dependencias y aislamiento del entorno de desarrollo, con un archivo `requirements.txt` versionado en el repositorio.

_Despliegue_

- **Gunicorn** como servidor WSGI de producción, expuesto detrás de **Cloudflare** como _reverse proxy_, sobre la máquina virtual con dominio propio exigida por RNF-01 y RNF-02. Todo el stack es software libre, en cumplimiento con la limitación del proyecto.

_Documentación y control de versiones_

- **Obsidian / Markdown** para mantener la documentación de diseño junto al código fuente.
- **Git + GitHub** para el repositorio público con commits incrementales y _release_ final exigidos en la rúbrica.

**Notaciones de diseño**

- **Diagrama E/R** en notación de Chen extendida (con soporte para herencia y especialización), por ser la utilizada en el curso.
- **Esquema relacional** en notación textual estándar `R(A1, A2, …, An)`, con atributos clave subrayados y claves foráneas indicadas mediante flechas o anotaciones explícitas.
- **DDL de SQL** como representación final ejecutable del esquema, generada a partir del modelo relacional.
- **Diagramas UML de casos de uso** para los nueve requisitos funcionales.
- **Diagrama de arquitectura MVC** mostrando las tres capas (Modelo, Vista/Plantilla, Controlador/Ruta Flask), sus responsabilidades y el flujo de una petición HTTP desde el navegador hasta MySQL y de vuelta.
- **Diagramas de flujo** para los procesos críticos de autenticación (RF-01, RF-02) y de inserción y modificación de datos (RF-08, RF-09).