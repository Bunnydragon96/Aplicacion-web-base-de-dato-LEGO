## Definición del problema
El cliente (profesor) quiere que practiquemos como implementar una base de datos a una aplicación web usando técnicas aprendidas en clase. 

## Antecedentes
MongoDB¹ es una plataforma de visualización e interacción con bases de datos no estructurados. Sin embargo, desde 20250, tiene un *dashboard*, puede crear analíticas de los datos y cumple con ACID², entre otros *features*. Apoya queries, indexación, replicación, load balancing, almacenamiento de archivos, agregación, capped collections y transacciones. A pesar de estos features, la comunidad ha encontrado riesgos de seguridad en la aplicación.   

¹ https://en.wikipedia.org/wiki/MongoDB
¹ https://github.com/mongodb/mongo
² https://en.wikipedia.org/wiki/ACID

Brickset³
> Brickset is primarily a [database of LEGO sets](https://brickset.com/sets). We've been online since 2000 and are now a cornerstone of the online LEGO community: a resource used and trusted by LEGO fans around the world.
   As well as virtually every LEGO set ever made, our database also contains information about [minifigs](https://brickset.com/minifigs), [parts](https://brickset.com/parts), [colours](https://brickset.com/colours), set inventories and much more. We also maintain comprehensive [lists of discounts and new products](https://brickset.com/buy) at online LEGO retailers, making it easy to grab a bargain or bag the latest set.

³ https://brickset.com/ 

## Objetivo general: 
Implementar una aplicación web sencilla para visualizar la base de datos que escogimos para este proyecto *lego_sets.csv*.

## Objetivos específicos:

| #   | Objetivo                                                                                                                                                                               |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Realizar estudio de factibilidad                                                                                                                                                       |
| 2   | Implementar un sistema de de inicio de sesion para la gestión de usuarios.                                                                                                             |
| 3   | Analizar el dataset de lego_set.csv escogida.                                                                                                                                          |
| 4   | Crear al menos 8 entidades y 6 relaciones que satisface al cliente.                                                                                                                    |
| 5   | Describir las dependencias funcionales y restricciones.                                                                                                                                |
| 6   | Normalizar las tablas a 3NF o BCNF.                                                                                                                                                    |
| 7   | Mostrar al profesor a ser aprobado.                                                                                                                                                    |
| 8   | Convertir archivo .csv $\rightarrow$ .db y .sql                                                                                                                                        |
| 9   | Implementar la base de datos a la aplicación web.                                                                                                                                      |
| 10  | Implementar una interfaz que permita por lo menos 5 queries. Incluir: al menos 1 JOIN de 3 o más tablas, 1 consulta con agregación (GROUP BY / HAVING), y 1 subconsulta con o sin WITH |
| 11  | Implementar una interfaz que permita insertar y modificar datos                                                                                                                        |

## Alcance

El proyecto será una aplicación web que permitirá al usuario visualizar, modificar, insertar y hacer los procesos anteriormente dichos con la base de datos creada de *lego_sets.csv*. Esta página está dedicada a personas familiarizadas con bases de datos y saben como interactuar con ellos. Se hará la inspección de los datos y el proceso en como se transformaron de .csv a una base de datos compatible con SQL con su diagrama **E/R** correspondiente cumpliendo con **3NF** o **BCNF**. 
Esta aplicación tendrá una página de registro y será servida usando una **máquina virtual (VM) y dominio** propio.

## Limitaciones

Se usarán recursos de software libres.