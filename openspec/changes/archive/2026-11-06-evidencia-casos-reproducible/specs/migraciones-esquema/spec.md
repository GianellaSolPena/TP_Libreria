# Spec Delta

## MODIFIED Requirements

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
