# migraciones-esquema Specification

## Purpose

Garantiza que el esquema de la base se crea y se revierte sólo con migraciones Alembic versionadas y legibles, y que la base misma impide modificar o borrar el historial de movimientos de stock, venga el pedido de donde venga.

## Requirements

### Requirement: Esquema sólo con Alembic
El esquema SHALL crearse exclusivamente aplicando las migraciones Alembic; la aplicación y los scripts MUST NOT crear tablas con `create_all` ni con SQL suelto.

#### Scenario: Sin create_all en el código
- **WHEN** se busca `create_all` en `parcial/` (sin `.venv`)
- **THEN** no aparece ninguna llamada

### Requirement: Dos migraciones nuevas sobre las del TP
A las migraciones `0001` y `0002` del TP SHALL sumarse exactamente dos: `0003` (tablas de acceso, `movimiento_stock` y cambios de `cliente` y `libro`), generada con `--autogenerate`, y `0004` (sólo agregado), escrita a mano. Cada una MUST llevar un comentario que diga cómo se obtuvo, que fue leída antes de aplicarse y qué se corrigió a mano y por qué.

#### Scenario: Historial lineal
- **WHEN** se ejecuta `alembic history` desde `parcial/`
- **THEN** muestra la cadena `0001 -> 0002 -> 0003 -> 0004` con `0004` como head

#### Scenario: Comentarios de origen
- **WHEN** se abren los archivos de `0003` y `0004`
- **THEN** el docstring de `0003` declara que es autogenerada, leída antes de aplicar y lista cada corrección manual con su motivo, y el de `0004` declara que es a mano porque la comparación automática no ve funciones ni disparadores

### Requirement: Ciclo upgrade, downgrade, upgrade
Sobre una base vacía, `alembic upgrade head`, luego `alembic downgrade base` y otra vez `alembic upgrade head` SHALL terminar sin errores, dejando tras el downgrade la base sin tablas del proyecto ni funciones o disparadores residuales. La salida completa de los tres comandos, junto con el estado de la base después de cada uno (tablas, revisión de `alembic_version` y existencia de la función del disparador), MUST guardarse en `parcial/evidencia/`, tomada sobre una base PostgreSQL 16 descartable, con un encabezado que indique cómo se obtuvo y sin contraseñas.

#### Scenario: Ciclo completo en base vacía
- **WHEN** sobre una base vacía se corren `upgrade head`, `downgrade base` y `upgrade head`
- **THEN** los tres comandos terminan con código 0 y el esquema final es igual al del primer `upgrade head`

#### Scenario: Downgrade sin residuos
- **WHEN** tras `upgrade head` se corre `downgrade base`
- **THEN** sólo queda la tabla `alembic_version` y no existe la función del disparador de sólo agregado

#### Scenario: Downgrade restaura el UNIQUE del ISBN
- **WHEN** se corre `alembic downgrade 0002`
- **THEN** `libro` vuelve a tener el UNIQUE común `uq_libro_isbn` y no tiene `borrado_en`

#### Scenario: Evidencia del ciclo
- **WHEN** se lee el archivo del ciclo en `parcial/evidencia/`
- **THEN** muestra las líneas `Running upgrade` de 0001 a 0004, las `Running downgrade` de 0004 a 0001 y otra vez las de upgrade, cada una seguida del estado de la base, y el estado final es igual al del primer `upgrade head`

### Requirement: Modelos y migraciones sin diferencias
Tras `alembic upgrade head`, la comparación automática de Alembic entre los modelos y la base SHALL no detectar diferencias.

#### Scenario: Autogenerate vacío
- **WHEN** con la base en head se ejecuta `alembic check`
- **THEN** informa que no hay operaciones nuevas pendientes

### Requirement: Movimientos de stock de sólo agregado
La base SHALL rechazar todo UPDATE y todo DELETE sobre filas de `movimiento_stock`, sin importar desde dónde se ejecute (aplicación, psql u otro cliente), mediante un disparador instalado por la migración `0004`. INSERT MUST seguir permitido.

#### Scenario: UPDATE rechazado
- **WHEN** en psql se ejecuta un UPDATE sobre una fila existente de `movimiento_stock`
- **THEN** la base responde con un error del disparador y la fila no cambia

#### Scenario: DELETE rechazado
- **WHEN** en psql se ejecuta un DELETE sobre una fila existente de `movimiento_stock`
- **THEN** la base responde con un error del disparador y la fila sigue existiendo

#### Scenario: INSERT permitido
- **WHEN** se inserta un movimiento válido
- **THEN** la base lo acepta

#### Scenario: TRUNCATE no bloqueado
- **WHEN** se ejecuta `TRUNCATE movimiento_stock ... CASCADE` (vaciado de datos de prueba)
- **THEN** la base lo acepta, porque el disparador es por fila y sólo cubre UPDATE y DELETE

### Requirement: Script de demostración del caso C-14
`parcial/test/solo_agregado.sql` SHALL demostrar en psql que UPDATE y DELETE sobre `movimiento_stock` son rechazados por el disparador, funcionando tanto sobre una base recién migrada como sobre una con datos iniciales, y sin dejar filas nuevas al terminar. La salida de una corrida sobre la base cargada con `python seed.py` MUST guardarse en `parcial/evidencia/` como captura del caso C-14.

#### Scenario: Ejecución del script
- **WHEN** se ejecuta `psql -f test/solo_agregado.sql` contra la base en head
- **THEN** la salida muestra un error del disparador para el UPDATE y otro para el DELETE, y al terminar la base tiene las mismas filas que antes

#### Scenario: Captura entregable
- **WHEN** se revisa `parcial/evidencia/` después de correr el script sobre los datos iniciales
- **THEN** hay un archivo con la salida de psql que muestra los dos rechazos y que el conteo de movimientos antes y después es 7
