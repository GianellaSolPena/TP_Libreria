# CHANGES — Secuencia de Implementación

> Índice de los changes del **TP Librería — Parcial Cap 1-6** (FastAPI + SQLModel + SQLAlchemy async + PostgreSQL 16 + Alembic).
> Alcance: **sólo lo que pide `Parcial_Cap1a6_Consigna.pdf`**. Checklist de cobertura: `knowledge-base/13_auditoria_vs_pdf.md`.
> **Leer este archivo antes de cada `/opsx:propose`.**

## Changelog
- **2026-11-03 — Plan reducido a lo básico del PDF**: sin pytest ni TDD (DD-01 reemplazada); las pruebas son las del PDF (`.http` con respuesta esperada en comentario + `test/solo_agregado.sql`) y la evidencia C-14/C-15 y D. Changes agrupados por ejercicio. Mapeo: antes C-01 → C-01; C-02 (infra pytest) → eliminado; C-03 → C-02; C-06+C-07 → C-03; C-04+C-05 → C-04; C-08+C-09 → C-05; C-10+C-11 → C-06; C-12+C-13+C-14 → C-07; C-15 → C-08; C-16+C-17+C-18 → C-09; C-19+C-20 → C-10; C-21 → C-11; C-22 → C-12.
- **2026-11-03 — Auditoría contra el PDF** (`13_auditoria_vs_pdf.md`): correcciones de endpoints, modelo, RN y estructura incorporadas al scope de cada change (los ids de la auditoría son los anteriores; ver mapeo arriba).

## Premisas (no negociables)
1. `parcial/` es la copia del TP entregado (`e337710`) y se evoluciona ahí; la raíz del repo solo tiene planificación (el TP original se quitó el 2026-11-03; sigue en `e337710`). Comandos del parcial (alembic, uvicorn, seed) se corren desde `parcial/`.
2. `despliegue/` es la copia **congelada** del TP + Dockerfile (Ej. 9-10); no lleva nada del parcial.
3. `main.py` y `seed.py` en la raíz de `parcial/` (DD-08; se revierte sólo si Q-03 dice otra cosa). `despliegue/` sigue con `app.main:app`.
4. **Capas** (PDF p. 8-9): el router construye el UoW con una dependencia, llama al servicio y traduce errores; el servicio abre el UoW con `async with`, nunca recibe la sesión ni hace commit/rollback; los repositorios hacen `flush()`, nunca `commit()`; el UoW confirma/revierte al salir y no cierra la sesión. Única excepción: `intento_acceso` (DD-09).
5. Verificación de cada change = los casos `.http` / chequeos manuales que el PDF describe para esa parte.

## Orden y dependencias

```
C-01 copias (hecho)
├── C-02 config-lifespan-health (hecho)
│   ├── C-03 modelos-migraciones (hecho) ─┐
│   └── C-04 core-capas-catalogo (hecho) ─┴── C-05 autenticacion
│                                      └── C-06 autorizacion-roles-eventos
│                                           └── C-07 libros-clientes-ventas (+C-03, C-04)
│                                                └── C-08 lecturas-sin-n1
│                                                     └── C-09 seed-casos-readme
└── C-10 despliegue-imagen (sólo despliegue/, en paralelo) (hecho)
     └── C-11 despliegue-vps (hecho)
C-12 empaquetado-zip (C-09 + C-11)
```

Uso: tomar el próximo `[ ]` con dependencias en `[x]`, leer sus "Leer antes", `/opsx:propose` → `/opsx:apply` → `/opsx:archive`, marcar `[x]`.

---

### [C-01] `snapshots-parcial-despliegue`
- **Estado**: `[x]` completo y archivado (2026-11-03)
- **Scope**: `parcial/` y `despliegue/` como copias idénticas de `e337710` (sin `.venv`, `__pycache__`, `.env`, `.git`); tag `tp-cap1a4-entregado`.
- **Dependencias**: ninguna · **Governance**: MEDIO · **Ej.**: habilita 1-10
- **Leer antes**: `09` (DD-03), `12` §Contenido del .zip

### [C-02] `config-lifespan-health`
- **Estado**: `[x]` completo (2026-11-03)
- **Scope**:
  - `app/core/config.py` con `pydantic-settings`: `POSTGRES_USER/PASSWORD/DB/HOST/PORT` + URL `postgresql+asyncpg` con `@computed_field`, `SQL_ECHO`, pool, duración del token, costo bcrypt, cookie `Secure` (nombres: Q-04). Clave de firma y `POSTGRES_PASSWORD` **sin default** (si faltan no arranca; nada de clave generada al arrancar); `.env` no versionado
  - `app/core/database.py`: funciones que crean motor (`echo=SQL_ECHO`, pool) y fábrica (`expire_on_commit=False`), no llamadas al importar; `get_session` toma la fábrica de `app.state`, una sesión por petición, la cierra
  - `parcial/main.py`: lifespan crea motor y fábrica en `app.state`, calcula una vez el hash ficticio (lo completa C-05), `dispose()` al apagar
  - `GET /health/live` sin base; `GET /health/ready` `SELECT 1` → 200 o 503 (IN-07); `health` sólo `router.py`
  - `migrations/env.py` usa `Settings` (sin credenciales en `alembic.ini`); `env.example` con todas las variables sin secretos; `requirements.txt` con pydantic-settings, bcrypt, PyJWT
- **Verificación**: arranca con `.env`; sin clave o sin contraseña no arranca; live 200 con base caída y ready 503
- **Dependencias**: C-01 · **Governance**: ALTO (config y secretos) · **Ej.**: 1 (6 pts)
- **Leer antes**: `08` §Variables de entorno y §Estructura; `11` (Config, Motor, Health); `10` (Q-04, IN-07)

### [C-03] `modelos-migraciones`
- **Estado**: `[x]` completo y archivado (2026-11-03)
- **Scope**:
  - `usuarios/models.py`: `Usuario` (email UNIQUE, nombre, password_hash, activo, debe_cambiar_password; sin columna rol), `AsignacionRol` (CHECK rol IN ADMIN/VENDEDOR/CLIENTE, `desde`, `vence_en`/`revocada_en`/`otorgada_por` nulos [Q-17], único parcial `(usuario_id, rol) WHERE revocada_en IS NULL`), `IntentoAcceso` (índice `(email, ip, cuando)`), `EventoSeguridad` (actor texto, sin FK)
  - `libros/models.py`: `MovimientoStock` (`venta_id` nulo, `usuario_id` NOT NULL, CHECK `cantidad <> 0`); `Libro.borrado_en` + único parcial de `isbn` `WHERE borrado_en IS NULL` en lugar de `uq_libro_isbn`; siguen CHECK precio > 0 y stock >= 0
  - `clientes/models.py`: `Cliente.usuario_id` nulo UNIQUE FK; `Cliente.usuario` devuelve un objeto
  - Fechas `timestamptz`, dinero `NUMERIC`, nulo sólo donde el PDF dice "(nulo)", índice en cada FK nueva, `back_populates` en los dos extremos; tablas que no cambian quedan igual; nombres del PDF se agregan, no se quitan
  - **0003** `--autogenerate`, leída antes de aplicar y con comentario; correcciones a mano comentadas (drop `uq_libro_isbn`, sin drops espurios); downgrade completo. Backfill "Stock inicial" según Q-08
  - **0004 a mano** (comentario: autogenerate no ve funciones ni disparadores): disparador que rechaza UPDATE y DELETE sobre `movimiento_stock` venga de donde venga; downgrade lo quita (TRUNCATE no se bloquea, DD-10)
  - `parcial/test/solo_agregado.sql` (caso C-14). Esquema sólo con Alembic, nunca `create_all`
- **Verificación**: `upgrade head` en base vacía → `downgrade base` → `upgrade head`; `solo_agregado.sql` en psql rechaza UPDATE/DELETE
- **Dependencias**: C-02 · **Governance**: ALTO (esquema y DDL a mano) · **Ej.**: 2 (10), 7 (disparador)
- **Leer antes**: `04`; `11` §Riesgos de la migración; `05` §Sólo agregado; `10` (IN-01, Q-08, Q-17)

### [C-04] `core-capas-catalogo`
- **Estado**: `[x]` completo y archivado (2026-11-03)
- **Scope**:
  - `app/core/repository.py`: `BaseRepository[T]` (recibe sesión y clase del modelo; `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`; `flush`, nunca `commit`) y `SoftDeleteRepository[T]` (filtra dados de baja; `get_by_id_including_deleted`, `soft_delete`)
  - `app/core/unit_of_work.py`: commit al salir, rollback con excepción, no cierra la sesión; patrón de UoW por módulo y dependencia del router que lo construye
  - `app/core/paginacion.py`: `{items,total,page,size,pages}`, page >= 1, size 1..100 (20), página de más 422 ("La página 4 no existe: hay 3"), total con los mismos filtros
  - Traducción de errores en el router: `IntegrityError` → 409 con mensaje propio, sin texto de la base; unicidad sin consulta previa
  - Refactor de `editoriales`, `generos`, `autores` con `schemas`/`repository`/`unit_of_work`/`service`/`router`: contratos separados, `extra="forbid"`, PATCH con `exclude_unset`; `GET /editoriales`, `/generos` paginados; `POST` 201/409/422; `PATCH /editoriales/{id}`, `/autores/{id}`; rutas sin barra final (IN-05); rutas extra del TP según Q-10
- **Verificación**: pedidos manuales (luego en `.http` de C-09): 409 duplicado, 422 por campo extra, PATCH parcial, listado paginado
- **Dependencias**: C-02 · **Governance**: MEDIO · **Ej.**: 6 (base), 3 (parte)
- **Leer antes**: `08` §Capas, UoW y repositorios; `05` §Paginación y §Errores; `06` §Catálogo

### [C-05] `autenticacion`
- **Estado**: `[x]` completo y archivado (2026-11-05)
- **Scope**:
  - `app/core/security.py`: bcrypt siempre con `asyncio.to_thread` bajo semáforo, costo desde `Settings`, > 72 bytes rechazado; hash ficticio real en el lifespan; JWT (PyJWT) con `sub`, `exp` y roles vigentes; cookie `access_token` HttpOnly, SameSite=Lax, Max-Age, Secure configurable; nunca en el cuerpo
  - Módulo `usuarios` por capas (repos: usuario, asignación, intento, evento); contratos `extra="forbid"`, contraseñas <= 72 bytes → 422, nunca `password_hash` en respuestas
  - `POST /auth/registro` (201/409/422): hash antes del UoW; usuario + rol CLIENTE + ficha de cliente en un bloque; correo repetido (usuario o cliente) → 409 por UNIQUE, sin filas sueltas (Q-09)
  - `POST /auth/login` (200/401/422/429): primero conteo de fallos (email, ip) en 60 s desde el último login correcto → 429 + `Retry-After` sin hash; luego hash real o ficticio; 401 igual exista o no el correo; cuerpo `{mensaje, debe_cambiar_password, expira_en_segundos}`
  - `POST /auth/logout` (borra la cookie), `GET /auth/yo` (usuario, roles vigentes y del token), `POST /auth/cambiar-password` (hash antes del UoW; contraseña + `debe_cambiar_password=false` + evento en un bloque; no emite token ni invalida sesiones; Q-11)
  - `intento_acceso` en sesión y transacción propias, siempre confirmadas (DD-09), con comentario de qué/por qué/costo (Q-20)
- **Verificación**: casos C-02..C-05 del PDF
- **Dependencias**: C-03, C-04 · **Governance**: CRITICO · **Ej.**: 4 (14), 7 (intento de acceso)
- **Leer antes**: `05` §Auth y §Límite de intentos; `07` §Registro y login; `08` §Seguridad; `10` (Q-04, Q-09, Q-11, Q-20)

### [C-06] `autorizacion-roles-eventos`
- **Estado**: `[x]` completo y archivado (2026-11-05)
- **Scope**:
  - `app/core/dependencies.py`: `get_usuario_actual` (ya creada en C-05 con todo el 401; aquí sólo se amplía para cargar los roles vigentes en la misma lectura, D1), roles vigentes de `asignacion_rol` en cada petición, control del cambio obligatorio, `requiere_rol` (403); misma sesión que el UoW
  - Dos grupos de rutas en `main.py`: abierto (health, `/auth/*`, catálogo público) y protegido con el control del cambio obligatorio montado una vez; matriz de permisos de `03`
  - `POST /usuarios` (ADMIN; 201/409/422; alta de personal con contraseña provisoria hasheada antes del UoW, cambio obligatorio, rol y evento en un bloque); `GET /usuarios/{id}/roles`; `POST /usuarios/{id}/roles` (`vence_en` opcional, con zona y futuro, si no 422); `DELETE /usuarios/{id}/roles/{rol}` (escribe `revocada_en`, nunca borra)
  - RN-03 segunda asignación abierta 409; reasignar un vencido cierra la fila y abre otra; RN-05 no revocarse el ADMIN propio ni quedar sin admins → 409
  - RN-16 evento en la misma transacción (alta de personal, asignar, revocar); actor `SISTEMA` para datos iniciales; `GET /eventos` (ADMIN, paginado)
- **Verificación**: casos C-01, C-06 (401/403), C-07, C-08, C-09
- **Dependencias**: C-05 · **Governance**: CRITICO · **Ej.**: 5 (12), 7 (eventos)
- **Leer antes**: `03` (matriz); `05` §Autorización, §Roles, §Eventos; `04` §asignacion_rol; `10` (Q-05, Q-12)

### [C-07] `libros-clientes-ventas`
- **Estado**: `[x]` completo (2026-11-05; archivado)
- **Scope**:
  - **Libros** (repos: libro sobre `SoftDeleteRepository`, `LibroAutor`, `MovimientoStock`): `POST /libros` con `autores` y `stock_inicial` (libro + autorías + "Stock inicial" en un bloque); `PATCH /libros/{id}` sólo título/precio (`stock` → 422); `DELETE` baja lógica 204; `POST /libros/{id}/reponer` (dado de baja → 409); `GET /libros/{id}/movimientos` (Q-18); reuso de ISBN tras la baja
  - **Punto único de escritura de stock** (alta, reposición, venta): actualiza `libro.stock` y agrega el movimiento con el `usuario_id` del actor
  - Catálogo público sin dados de baja: `GET /libros` (page, size, `titulo` ILIKE ligado, `genero_id`), `GET /libros/{id}` (Q-19), `/{editoriales,generos,autores}/{id}/libros`
  - **Clientes** y perfil por capas: `POST /clientes`, `GET`/`PATCH /clientes/{id}`, `POST /clientes/{id}/perfil`, `GET /clientes/{id}/ventas` (VENDEDOR, ADMIN; 409 por correo vía UNIQUE)
  - **Ventas**: UoW que compone repos de ventas, clientes y libros; contrato `cliente_id` + `renglones` (>= 1, sin repetidos, cantidad > 0; sin precio/total/fecha; sin PATCH); `POST /ventas` en un bloque (precio copiado, total del servidor, descuento y un movimiento negativo por renglón); 409 sin escrituras si falta stock o cliente/libro inexistente o dado de baja
  - Aviso `BackgroundTasks` (`sleep(0.5)` + log) sólo si confirmó, visible en uvicorn tras la respuesta
  - `GET /ventas` (VENDEDOR, ADMIN, paginado); `GET /ventas/{id}` sin `requiere_rol` (el servicio decide: personal o dueño, si no 403); `GET /mis-ventas`
- **Verificación**: casos C-06 (lo propio), C-10, C-11, C-12, C-13; `stock == SUM(movimientos)` tras cada venta
- **Dependencias**: C-03, C-04, C-06 · **Governance**: ALTO (transacción y stock) · **Ej.**: 6 (16), 3 (parte), 5 (lo propio), 8 (aviso)
- **Leer antes**: `05` §Stock, §Borrado lógico, §Ventas; `07` §Reposición y baja, §Venta; `04` §libro, movimiento_stock, cliente; `10` (Q-07, Q-08, Q-10, Q-18, Q-19)

### [C-08] `lecturas-sin-n1`
- **Estado**: `[x]` completo (2026-11-05; archivado)
- **Scope**:
  - Precarga dentro del método del repositorio; detalle de venta con cantidad fija de consultas (incluye libro dado de baja); ninguna carga perezosa
  - Repaso final: todos los listados paginados con total filtrado; búsqueda ligada; ningún 500 por entrada inválida (incluye ids fuera de `int4`); handlers `async def` sin llamadas bloqueantes; `grep` de `AsyncSession`/`commit(` en `service.py`/`router.py` vacío (salvo DD-09)
- **Verificación**: caso C-15 con `SQL_ECHO=true` (misma cantidad de consultas con 2 y 4 renglones, salida a `parcial/evidencia/`); caso C-16
- **Dependencias**: C-07 · **Governance**: MEDIO · **Ej.**: 8 (6), 3 (cierre)
- **Leer antes**: `05` §Lecturas y §Paginación; `07` §Detalle de venta
- **Notas de cierre (QA-03)**: C-08 dejó `parcial/test/C-15_detalle_consultas_fijas.http` y la evidencia `parcial/evidencia/C-15_consultas_detalle_venta.txt` sobre datos de prueba `c08.`; **C-09 regenera la evidencia C-15 tras `python seed.py` y retira `test/C-07_consultas_fijas.http` del TP**. Sin migración (sólo `lazy="raise_on_sql"` en los 26 `Relationship`).

### [C-09] `seed-casos-readme`
- **Estado**: `[x]` completo (2026-11-06; archivado en `openspec/changes/archive/2026-11-06-seed-casos-readme/`)
- **Scope**:
  - `parcial/seed.py`: `TRUNCATE ... RESTART IDENTITY CASCADE` (DD-10) y datos del PDF: 3 editoriales, 3 géneros, 6 autores, 5 libros (IN-02/IN-03), Lucía con perfil, Tomás, Ana Paz con usuario; usuarios admin, admin2, vendedor, ana, nuevo (cambio obligatorio; contraseñas de mentira, Q-05); venta 1 de Lucía (69000.00) por vendedor; movimientos "Stock inicial" y salidas (Q-08); evento `SISTEMA` "Carga de los datos iniciales"
  - `parcial/test/*.http` para los casos C-01..C-16 (IN-04), respuesta esperada en comentario, varias sesiones (`# @name`, `# @no-cookie-jar`, `Cookie:`), precedidos de `python seed.py`; retirar `test/seed.sql` si queda obsoleto
  - `parcial/evidencia/`: consultas C-15 y captura de psql de C-14
  - `parcial/README.md`: integrantes (Q-06), venv, dependencias, `.env` y cómo generar la clave de firma, `alembic upgrade head`, `python seed.py`, arranque; verificado desde cero
- **Verificación**: correr todos los `.http` contra uvicorn tras `python seed.py`
- **Dependencias**: C-06, C-08 · **Governance**: BAJO · **Ej.**: evidencia de 3-8, requisito de entrega
- **Leer antes**: `12` §Casos C y §README; `10` (IN-02..IN-05, Q-05, Q-06, Q-08)
- **Notas de cierre**: C-09 dejó `parcial/seed.py`, 15 `.http` en `parcial/test/` (C-01..C-16 salvo C-14), evidencia C-14/C-15 en `parcial/evidencia/` y `parcial/README.md`; retirados los `.http` y `seed.sql` del TP.

### [C-10] `despliegue-imagen`
- **Estado**: `[x]` hecho (2026-11-06)
- **Scope** (sólo `despliegue/`):
  - Corregir sólo defectos propios del TP: IN-07 (`/health/ready` 503) e IN-06 (datos iniciales sin `psql` en Alpine); anotarlos para DEPLOY.md
  - `Dockerfile`: `FROM python:3.12-alpine`, `requirements.txt` antes del código con `--no-cache-dir`, usuario sin privilegios + `USER`, `sh -c "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"`, `HEALTHCHECK` con `wget http://127.0.0.1:8000/health/ready`; sin Compose
  - `.dockerignore` (`.env`, `.venv`, `.git`, `__pycache__`); `env.example` con la forma de `DATABASE_URL`
- **Verificación**: D-01, D-02, D-04..D-07 en local (base `python:3.12-alpine` < 100 MB, `healthy`, sin `.env` ni secretos, no root, falla sin `DATABASE_URL`)
- **Dependencias**: C-01 · **Governance**: ALTO (secretos en imagen) · **Ej.**: 9 (11)
- **Leer antes**: `12` §Dockerfile y §Casos D; `10` (IN-06, IN-07)

### [C-11] `despliegue-vps`
- **Estado**: `[x]` hecho (2026-11-06). Notas de cierre: TP en línea en `http://187.127.58.90:8101` (contenedor `libreria`, imagen construida en el servidor, base `libreria` con rol propio en `grupo1-chicas_db` vía red `easypanel-grupo1-chicas`, env-file `/root/libreria/libreria.env` 600 fuera del repo); evidencia D-01..D-08 del VPS en `despliegue/evidencia/` (la local de C-10 en `evidencia/local/`); no hizo falta regla `ufw` (4.2 condicional no ejecutada); foto previa/posterior del servidor sin cambios ajenos. Riesgos anotados en `DEPLOY.md`: tras reiniciar el VPS puede hacer falta `docker start libreria`, servidor compartido de 1 CPU, PG17 en el servidor vs 16 local. Mantener el servicio arriba hasta que se publiquen las notas
- **Scope**: `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file <archivo> libreria` (`--add-host` si corresponde; `SQL_ECHO=false`); datos iniciales vía `docker exec`; `despliegue/DEPLOY.md` (URL, fecha y hora, comandos completos, cambios al TP, cómo se actualiza, build en servidor o imagen llevada); `despliegue/evidencia/` con D-01..D-08 (Q-14)
- **Dependencias**: C-10 (Q-02 resuelta) · **Governance**: ALTO · **Ej.**: 10 (7)
- **Leer antes**: `12` §DEPLOY.md y §Casos D; `07` §Flujo 7; `10` (Q-02, Q-14)

### [C-12] `empaquetado-zip`
- **Estado**: `[ ]` pendiente
- **Scope**: `Parcial_Cap1a6_<Grupo>.zip` (Q-01) con `parcial/` y `despliegue/` según el árbol del PDF; sin `.venv`, `__pycache__`, `.env`; `.git` según Q-15; nada de la raíz, `knowledge-base/`, `openspec/`, `.claude/`. Verificar: búsqueda de secretos y `alembic upgrade head` + `python seed.py` desde el zip extraído
- **Dependencias**: C-09, C-11 · **Governance**: ALTO (filtrar credenciales) · **Ej.**: requisito de entrega
- **Leer antes**: `12` §Contenido del .zip y §Reglas duras; `10` (Q-01, Q-13, Q-15)

---

## Resumen

| ID | Change | Ej. / pts | Governance | Depende de |
|----|--------|-----------|------------|------------|
| C-01 | snapshots-parcial-despliegue `[x]` | habilita todo | MEDIO | — |
| C-02 | config-lifespan-health `[x]` | Ej.1 (6) | ALTO | C-01 |
| C-03 | modelos-migraciones `[x]` | Ej.2 (10), Ej.7 | ALTO | C-02 |
| C-04 | core-capas-catalogo `[x]` | Ej.6, Ej.3 | MEDIO | C-02 |
| C-05 | autenticacion `[x]` | Ej.4 (14), Ej.7 | CRITICO | C-03, C-04 |
| C-06 | autorizacion-roles-eventos `[x]` | Ej.5 (12), Ej.7 | CRITICO | C-05 |
| C-07 | libros-clientes-ventas `[x]` | Ej.6 (16), Ej.3, Ej.5, Ej.8 | ALTO | C-03, C-04, C-06 |
| C-08 | lecturas-sin-n1 `[x]` | Ej.8 (6), Ej.3 (8) | MEDIO | C-07 |
| C-09 | seed-casos-readme `[x]` | evidencia + entrega | BAJO | C-06, C-08 |
| C-10 | despliegue-imagen `[x]` | Ej.9 (11) | ALTO | C-01 |
| C-11 | despliegue-vps `[x]` | Ej.10 (7) | ALTO | C-10 (+ Q-02) |
| C-12 | empaquetado-zip | entrega | ALTO | C-09, C-11 |

Rutas de `knowledge-base/` abreviadas por número (`05` = `knowledge-base/05_reglas_de_negocio.md`).

**Próximo change**: `C-12` (`empaquetado-zip`; C-11 hecho, grupo "Las chicas" → `Parcial_Cap1a6_Las chicas.zip`).
