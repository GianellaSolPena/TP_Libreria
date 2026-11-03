# Tasks

> Todo se corre desde `parcial/` con el `.venv` activo, `.env` válido y PostgreSQL 16 accesible. Sin pytest (DD-01): la verificación son los comandos de Alembic, `psql` y `solo_agregado.sql`. Antes de empezar, el usuario confirma las decisiones **[REVISAR]** de design.md (D-03, D-04, D-08, D-10).

## 1. Modelos de acceso y seguridad

- [x] 1.1 Crear `app/modules/usuarios/__init__.py` y `app/modules/usuarios/models.py` con `Rol(str, Enum)`, `Usuario` (`uq_usuario_email`, defaults `activo=True`, `debe_cambiar_password=False`), `AsignacionRol` (CHECK `ck_asignacion_rol_rol_valido`, `ux_asignacion_rol_usuario_rol_abierta` con `postgresql_where`, FK `otorgada_por` nula, índices `ix_asignacion_rol_usuario_id` e `ix_asignacion_rol_otorgada_por`, fechas `DateTime(timezone=True)`), `IntentoAcceso` (`ix_intento_acceso_email_ip_cuando`) y `EventoSeguridad` (sin FK), según D-02..D-05; verificar con `python -c "import app.modules.usuarios.models"` sin errores
- [x] 1.2 Declarar `Usuario.asignaciones` ↔ `AsignacionRol.usuario` con `foreign_keys` explícito (D-04); verificar con `python -c "from app.modules.models import metadata; from sqlalchemy.orm import configure_mappers; configure_mappers()"` sin `AmbiguousForeignKeysError`

## 2. Cambios en libro, cliente y venta

- [x] 2.1 En `libros/models.py`: `Libro.borrado_en` (timestamptz nula), quitar `unique=True` de `isbn` y agregar `Index("ux_libro_isbn_vigente", "isbn", unique=True, postgresql_where=text("borrado_en IS NULL"))` conservando los dos CHECK; agregar `MovimientoStock` (`venta_id` nulo, `usuario_id` NOT NULL, `motivo`, `cuando`, CHECK `ck_movimiento_stock_cantidad_no_cero`, tres índices de FK) y `Libro.movimientos` ↔ `MovimientoStock.libro`; verificar con `configure_mappers()` sin errores
- [x] 2.2 En `clientes/models.py`: `Cliente.usuario_id` nulo con FK a `usuario.id` y `uq_cliente_usuario_id`, nombrar `uq_cliente_email` en `__table_args__`, y `Cliente.usuario` ↔ `Usuario.cliente` (`uselist=False`); verificar que `Cliente.usuario.property.uselist` y `Usuario.cliente.property.uselist` son `False`
- [x] 2.3 En `ventas/models.py` agregar sólo `Venta.movimientos` ↔ `MovimientoStock.venta`, y `Usuario.movimientos` ↔ `MovimientoStock.usuario`; verificar con `configure_mappers()` y revisando que la definición de columnas de `Venta` no cambió (`git diff`)
- [x] 2.4 Registrar `usuarios` en `app/modules/models.py`; verificar que `metadata.tables` incluye las cinco tablas nuevas

## 3. Migración 0003 (autogenerada)

- [x] 3.1 Sobre una base vacía, `alembic upgrade head` (queda en 0002) y `alembic revision --autogenerate --rev-id 0003 -m "acceso movimientos borrado logico"`; verificar que el archivo existe con `down_revision = "0002"`
- [x] 3.2 Leer la 0003 completa y corregir según D-09 (drop `uq_libro_isbn`, `postgresql_where` en los dos únicos parciales, timestamptz, sin operaciones espurias sobre tablas del TP, orden de creación, `downgrade()` completo e inverso que recrea `uq_libro_isbn`), marcando cada corrección con `# FIX:`; verificar releyendo el diff contra los nombres de D-02
- [x] 3.3 Escribir el docstring de la 0003: autogenerada, leída antes de aplicar, lista de correcciones `FIX` con motivo, FKs sin cascada, sin backfill de "Stock inicial" (D-08) y límite del downgrade con ISBN repetidos; verificar que el docstring cubre esos puntos
- [x] 3.4 `alembic upgrade head` y `alembic check`; verificar que `check` no reporta operaciones (si reporta drift del TP, corregir sólo en el modelo según D-09 paso 5 y anotarlo)
- [x] 3.5 Comprobar en psql las restricciones de `specs/modelo-datos/spec.md` (inserciones manuales dentro de `BEGIN ... ROLLBACK`: ISBN repetido vigente rechazado y tras baja aceptado, segunda asignación abierta rechazada y tras revocar aceptada, rol inválido, cantidad 0, `usuario_id` nulo en movimiento, dos clientes con mismo usuario) y `\d` de las tablas para tipos `timestamptz` e índices; verificar que cada caso da el resultado del spec

## 4. Migración 0004 (a mano) y caso C-14

- [x] 4.1 `alembic revision --rev-id 0004 -m "disparador solo agregado"` y escribir `upgrade()`/`downgrade()` con `op.execute` según D-10 (función `movimiento_stock_solo_agregado`, disparador `tg_movimiento_stock_solo_agregado` `BEFORE UPDATE OR DELETE ... FOR EACH ROW`), con docstring que declara que es a mano porque el autogenerate no ve funciones ni disparadores; verificar con `alembic upgrade head` y `alembic history` mostrando `0001 -> 0002 -> 0003 -> 0004`
- [x] 4.2 Crear `parcial/test/solo_agregado.sql` autocontenido según D-11 (fixture propia en `BEGIN`, `SAVEPOINT` antes de UPDATE y de DELETE, `ROLLBACK` final, resultado esperado en comentario); verificar con `psql -v ON_ERROR_STOP=0 -f test/solo_agregado.sql` que aparecen los dos errores del disparador y que `SELECT count(*)` de las tablas tocadas no cambió
- [x] 4.3 Verificar que INSERT sigue permitido y que `TRUNCATE movimiento_stock CASCADE` no es bloqueado (dentro de `BEGIN ... ROLLBACK`)

## 5. Ciclo completo

- [x] 5.1 Sobre una base vacía: `alembic upgrade head` → `alembic downgrade base` → `alembic upgrade head`; verificar código 0 en los tres, que tras `downgrade base` sólo queda `alembic_version` y no existe la función `movimiento_stock_solo_agregado` (`\df`), y `alembic check` vacío al final
- [x] 5.2 `alembic downgrade 0002` y verificar con `\d libro` que vuelve `uq_libro_isbn` y no está `borrado_en`; luego `alembic upgrade head`
- [x] 5.3 Verificar que no hay `create_all` en `parcial/` (`grep -rn create_all parcial --exclude-dir=.venv` vacío) y que la app arranca (`uvicorn main:app`) y `GET /health/ready` responde 200

## Workflow follow-up

- Marcar `[x]` C-03 en `CHANGES.md` y archivar con `/opsx:archive modelos-migraciones`.
- Coordinar con C-04 si la tarea 3.4 obligó a tocar `editoriales/models.py` o `generos/models.py`.
