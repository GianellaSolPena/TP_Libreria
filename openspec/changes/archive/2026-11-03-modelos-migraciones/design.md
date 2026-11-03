# Design

## Context

- `parcial/` tiene el esquema del TP en `migrations/versions/0001_esquema_inicial.py` y `0002_agrega_genero.py`, con revision ids `"0001"`/`"0002"` (no hash) y docstrings que declaran las correcciones manuales con `FIX`. `env.py` (C-02) toma la URL de `Settings` y usa `app.modules.models.metadata` (SQLModel) como `target_metadata`; no hay `naming_convention`.
- Los modelos del TP declaran `Field(unique=True)` **sin nombre** (`libro.isbn`, `cliente.email`, `editorial.nombre`, `genero.nombre`), mientras 0001/0002 crearon `uq_*` con nombre. No existe todavía `app/modules/usuarios/`.
- Las relaciones del TP son `Relationship` de SQLModel con `back_populates`, carga perezosa por defecto (la precarga la resuelve C-08).
- Motivación y alcance: ver proposal.md. Requisitos: `specs/modelo-datos/spec.md` y `specs/migraciones-esquema/spec.md`.
- Governance ALTO: las decisiones marcadas **[REVISAR]** necesitan visto bueno del usuario antes de `/opsx:apply`.

## Goals / Non-Goals

**Goals:**
- Modelos SQLModel que reflejen exactamente la tabla del PDF (p. 5-6) y la Fig. 1, con restricciones con nombre estable.
- 0003 autogenerada y depurada, 0004 a mano; ciclo `upgrade head → downgrade base → upgrade head` limpio; `alembic check` vacío en head.
- Contrato de columnas estable para C-04/C-05/C-06/C-07.

**Non-Goals:**
- Ningún repositorio, servicio, router ni contrato (C-04..C-07). Los servicios del TP no se adaptan a `borrado_en` ni a movimientos acá.
- Carga de datos (`seed.py`, C-09) y backfill de datos existentes (ver D-08).
- Segundo mecanismo de sólo agregado por permisos del rol de base (DD-06).
- Estrategia de carga de relaciones (`lazy=`) — C-08.

## Decisions

### D-01 — Revision ids `0003` y `0004` con nombre descriptivo
`alembic revision --autogenerate --rev-id 0003 -m "acceso movimientos borrado logico"` y `alembic revision --rev-id 0004 -m "disparador solo agregado"`. Sigue la convención del TP (IN-01). Alternativa: hashes por defecto → rompe la lectura `0001→0004` que pide el PDF ("la tercera", "la cuarta").

### D-02 — Nombres explícitos para toda restricción e índice nuevo
Se declaran en `__table_args__` con nombre propio (patrón del TP: `uq_`, `ck_`, `ix_`, `fk_` implícito). Nombres:

| Objeto | Nombre |
|---|---|
| UNIQUE `usuario.email` | `uq_usuario_email` |
| CHECK rol | `ck_asignacion_rol_rol_valido` → `rol IN ('ADMIN','VENDEDOR','CLIENTE')` |
| Único parcial `(usuario_id, rol) WHERE revocada_en IS NULL` | `ux_asignacion_rol_usuario_rol_abierta` |
| Índices FK | `ix_asignacion_rol_usuario_id`, `ix_asignacion_rol_otorgada_por` |
| Índice `intento_acceso(email, ip, cuando)` | `ix_intento_acceso_email_ip_cuando` |
| CHECK `cantidad <> 0` | `ck_movimiento_stock_cantidad_no_cero` |
| Índices FK movimiento | `ix_movimiento_stock_libro_id`, `ix_movimiento_stock_venta_id`, `ix_movimiento_stock_usuario_id` |
| Único parcial `libro(isbn) WHERE borrado_en IS NULL` | `ux_libro_isbn_vigente` |
| UNIQUE `cliente.usuario_id` | `uq_cliente_usuario_id` |

Para `Libro` y `Cliente` (modelos que este change toca) también se nombran en el modelo las UNIQUE preexistentes que se conservan (`uq_cliente_email`) en lugar de `Field(unique=True)`, así modelo y base coinciden y el downgrade es legible. Alternativa: `naming_convention` global en `SQLModel.metadata` → renombraría en el modelo restricciones del TP ya creadas y el autogenerate propondría drops/creates en tablas que el PDF dice que "no cambian".

`asignacion_rol.usuario_id` lleva índice propio aunque exista el único parcial que empieza por `usuario_id`: el parcial no cubre las filas revocadas, y el historial de roles de un usuario las necesita (KB 04).

### D-03 — `Rol` como `enum.Enum` de Python, columna `VARCHAR` + CHECK (no ENUM nativo de PostgreSQL) **[REVISAR]**
`class Rol(str, Enum): ADMIN, VENDEDOR, CLIENTE` en `usuarios/models.py`; `rol: Rol = Field(sa_type=AutoString)` (o `sa_column=Column(String, ...)`) y el CHECK con nombre. El PDF pide literalmente "CHECK de rol" y tipar el atributo como `Rol`. Alternativa: dejar que SQLModel infiera `sa.Enum` → crea el tipo `rol` de PostgreSQL, el CHECK sería redundante, y el downgrade tiene que dropear el tipo a mano (el autogenerate no lo hace), rompiendo `downgrade base → upgrade head`.

### D-04 — `otorgada_por` FK a `usuario.id` con índice, sin relación ORM **[REVISAR — Q-17]**
FK nula a `usuario.id` + `ix_asignacion_rol_otorgada_por`. Como hay dos FKs `asignacion_rol → usuario`, `Usuario.asignaciones` y `AsignacionRol.usuario` llevan `foreign_keys` explícito (`sa_relationship_kwargs={"foreign_keys": "[AsignacionRol.usuario_id]"}` en `Usuario` y `"AsignacionRol.usuario_id"` en `AsignacionRol`). No se declara relación para el otorgante: la Fig. 1 no la dibuja y "navegación en los dos extremos" se exige sólo para las relaciones dibujadas. Alternativa: entero suelto sin FK → admite ids inexistentes y contradice "cada FK nueva lleva índice" sólo por omisión.

### D-05 — Defaults sólo del lado de Python
`desde`, `cuando` con `default_factory=lambda: datetime.now(timezone.utc)` y `sa_type=DateTime(timezone=True)`; `activo=True`, `debe_cambiar_password=False` como defaults de Python. Sin `server_default` (mismo criterio que `venta.fecha` en el TP; todas las escrituras pasan por el ORM o por `seed.py`). Consecuencia: el SQL manual (`solo_agregado.sql`) debe dar todos los valores. Alternativa: `server_default=sa.func.now()` → más cómodo en psql pero suma una diferencia de criterio con el TP sin que el PDF lo pida.

### D-06 — Baja lógica de `libro`: contrato hacia C-04/C-07
- Columna: `libro.borrado_en TIMESTAMPTZ NULL`. **Vigente ⇔ `borrado_en IS NULL`**; dar de baja = escribir `datetime.now(timezone.utc)`; nunca se vuelve a NULL (el PDF no pide reactivar).
- `SoftDeleteRepository[T]` (C-04) puede asumir que todo modelo con baja lógica expone el atributo `borrado_en: datetime | None` (hoy sólo `Libro`). Si C-04 eligió otro nombre, debe alinearse a `borrado_en` (nombre del PDF, no negociable).
- El índice `ux_libro_isbn_vigente` hace que un alta con ISBN de un vigente termine en `IntegrityError` (C-04 lo traduce a 409); un ISBN de un dado de baja entra.
- `Libro.isbn` pasa a `isbn: str` sin `unique=True` y el único va como `Index("ux_libro_isbn_vigente", "isbn", unique=True, postgresql_where=text("borrado_en IS NULL"))` en `__table_args__`.

### D-07 — Relaciones nuevas
| Lado A | Lado B | Notas |
|---|---|---|
| `Usuario.asignaciones: list[AsignacionRol]` | `AsignacionRol.usuario: Usuario` | `foreign_keys` explícito (D-04) |
| `Usuario.cliente: Optional[Cliente]` | `Cliente.usuario: Optional[Usuario]` | `uselist=False` en `Usuario`; en `Cliente` es many-to-one, ya escalar |
| `Usuario.movimientos` | `MovimientoStock.usuario` | |
| `Libro.movimientos` | `MovimientoStock.libro` | |
| `Venta.movimientos` | `MovimientoStock.venta: Optional[Venta]` | `ventas/models.py` sólo suma el atributo; la tabla `venta` no cambia |

Imports cruzados con `TYPE_CHECKING` como en el TP. Todas las FKs nuevas con `ON DELETE` por defecto (NO ACTION), explícito en el comentario de 0003: nada se borra en cascada; los libros se dan de baja lógicamente y los movimientos no se borran.

### D-08 — Sin backfill de "Stock inicial" en 0003 **[REVISAR — Q-08]**
`movimiento_stock.usuario_id` es NOT NULL (PDF + Fig. 1) y al aplicar 0003 no existe ningún usuario, así que un backfill tendría que inventar un usuario dentro de la migración. El PDF parte de base vacía + `python seed.py` (que hace `TRUNCATE ... CASCADE` y carga los "Stock inicial", C-09). Por lo tanto 0003 no backfillea y su docstring lo dice: sobre una base con libros del TP, `stock == SUM(movimientos)` no se cumple hasta correr el seed. Alternativa descartada: crear un usuario `SISTEMA` en la migración → mezcla datos con esquema y choca con el seed.

### D-09 — Generación y depuración de 0003
1. Base vacía → `alembic upgrade head` (queda en 0002).
2. Modelos nuevos listos y `usuarios` importado en `app/modules/models.py`.
3. `alembic revision --autogenerate --rev-id 0003 ...`.
4. Leer completa y corregir (cada corrección con `# FIX:` y listada en el docstring, como 0001):
   - Debe aparecer `op.drop_constraint("uq_libro_isbn", "libro", type_="unique")` + `create_index("ux_libro_isbn_vigente", ..., unique=True, postgresql_where=...)`; si el autogenerate no detecta el drop, se agrega a mano.
   - Quitar cualquier operación espuria sobre tablas que no cambian (drops/creates de `uq_*`/`ix_*` del TP por diferencias de nombre).
   - Verificar `postgresql_where` en los dos únicos parciales (el autogenerate a veces lo omite) y `DateTime(timezone=True)`.
   - Orden: crear `usuario` antes que `asignacion_rol`, `movimiento_stock` y la FK de `cliente`.
   - `downgrade()` completo e inverso: quitar FK/UNIQUE/columna de `cliente`, índice parcial y `borrado_en` de `libro`, recrear `uq_libro_isbn`, dropear índices y tablas nuevas. **Nota**: recrear `uq_libro_isbn` falla si hay dos libros con el mismo ISBN (uno dado de baja); se documenta en el docstring como límite del downgrade con datos.
5. `alembic upgrade head` → `alembic check` vacío. Si `check` reporta diferencias preexistentes del TP (p. ej. UNIQUE sin nombre en `editorial`/`genero`), se resuelven **sólo** en la declaración del modelo (nombrar la restricción) sin tocar la base; si eso toca `editoriales/models.py` o `generos/models.py`, coordinar con C-04 (ver Riesgos).

### D-10 — 0004 a mano: disparador por fila `BEFORE UPDATE OR DELETE`
```sql
CREATE FUNCTION movimiento_stock_solo_agregado() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'movimiento_stock es de sólo agregado: % no permitido', TG_OP
    USING ERRCODE = 'restrict_violation';
END $$;
CREATE TRIGGER tg_movimiento_stock_solo_agregado
  BEFORE UPDATE OR DELETE ON movimiento_stock
  FOR EACH ROW EXECUTE FUNCTION movimiento_stock_solo_agregado();
```
`downgrade()`: `DROP TRIGGER IF EXISTS ... ON movimiento_stock; DROP FUNCTION IF EXISTS movimiento_stock_solo_agregado();`. Vía `op.execute`. Docstring: escrita a mano porque el autogenerate no ve funciones ni disparadores.
- **Por fila y no por sentencia** **[REVISAR]**: DD-10 asume que `TRUNCATE` (usado por `seed.py`) no queda bloqueado; un disparador `FOR EACH ROW` sobre UPDATE/DELETE no se dispara con TRUNCATE y rechaza cualquier fila afectada. Costo: un UPDATE/DELETE que no afecta filas no da error (no hay nada que modificar). Alternativa: `FOR EACH STATEMENT` → también rechaza sentencias de 0 filas, pero no aporta protección real.
- `ERRCODE` explícito para que, si la app llegara a intentarlo, C-04 pueda traducirlo como error propio y no como 500 genérico.

### D-11 — `solo_agregado.sql` autocontenido con SAVEPOINT
Como el disparador es por fila, el script necesita al menos una fila. Para funcionar con o sin `seed.py` (C-09 llega después), abre `BEGIN`, inserta su propio usuario/editorial/libro/movimiento de prueba, y prueba `UPDATE` y `DELETE` cada uno tras un `SAVEPOINT` con `ROLLBACK TO SAVEPOINT` (en psql un error aborta la transacción); termina con `ROLLBACK`, así no deja filas. Corre con `psql -v ON_ERROR_STOP=0 -f test/solo_agregado.sql` y cada bloque lleva en comentario el error esperado. La captura de esa salida es la evidencia de C-14 (C-09 la guarda en `evidencia/`).

## Risks / Trade-offs

- [El autogenerate omite el drop de `uq_libro_isbn` o el `postgresql_where`] → D-09 paso 4: se revisa explícitamente y se corrige con `# FIX`.
- [Drift preexistente del TP hace fallar `alembic check`] → se corrige en el modelo sin migración; si toca módulos que C-04 refactoriza, sólo se cambian líneas de `__table_args__` de `models.py` y se avisa en el resumen para el merge.
- [Conflicto de archivos con C-04 en paralelo] → C-03 sólo toca `*/models.py`, `app/modules/models.py`, `migrations/` y `test/solo_agregado.sql`; C-04 no debería tocar ninguno de ellos salvo por D-09 paso 5.
- [Servicios del TP rompen la invariante de stock o fallan al crear libros sin movimientos] → aceptado hasta C-07; ningún caso del PDF se evalúa antes.
- [Carga perezosa en async sobre relaciones nuevas] → nadie las recorre todavía; C-08 define la precarga.
- [Downgrade de 0003 con ISBN repetidos entre vigente y dado de baja falla] → límite documentado; el ciclo exigido es sobre base vacía.
- [`TRUNCATE` permite vaciar `movimiento_stock`] → aceptado por DD-10; el PDF sólo exige rechazar UPDATE y DELETE.

## Migration Plan

Desde `parcial/` con `.env` válido y PostgreSQL 16 accesible: base vacía → `alembic upgrade head` → `alembic downgrade base` → `alembic upgrade head` → `alembic check` → `psql -f test/solo_agregado.sql`. Rollback del change: `alembic downgrade 0002` y revertir los archivos.

## Open Questions

- Q-07 (texto de `motivo`): no afecta el esquema (`motivo` es texto NOT NULL); se resuelve en C-07.
- Q-08 (usuario de los "Stock inicial" del seed): se resuelve en C-09; este change sólo fija que 0003 no backfillea (D-08).
