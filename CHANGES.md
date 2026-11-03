# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **TP Librería — Parcial Cap 1-6** (FastAPI + SQLModel + SQLAlchemy async + PostgreSQL 16 + Alembic).
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

## Changelog
- **2026-11-03 — Auditoría contra el PDF** (`knowledge-base/13_auditoria_vs_pdf.md`): tablas re-extraídas con `pdftotext -table` y Figura 1 leída como imagen. Correcciones: `POST /auth/logout` (no GET); `BaseRepository[T]` (no `Repository[T]`) con sus métodos mínimos; UNIQUE del ISBN real `uq_libro_isbn`; `movimiento_stock.usuario_id` NOT NULL; índices de FK, nulabilidad y relaciones en los dos extremos explícitos en C-06; eventos RN-16 también en alta de personal y cambio de contraseña; RN-03 (409), RN-05 (nunca cero admins), reasignación de rol vencido, `GET /usuarios/{id}/roles` y `GET /eventos` en C-11; `GET /libros/{id}/movimientos`, reponer/vender libro dado de baja 409 y listados sin dados de baja en C-12; archivos por capa explícitos en cada módulo; router traduce errores y servicios nunca tocan la sesión; `TRUNCATE` para seed/tests; ciclo upgrade→downgrade→upgrade; límite de 100 MB = imagen base; `main.py` en la raíz de `parcial/` (DD-08). Ids C-01..C-22 sin cambios.

**Premisas del proyecto (no negociables)**
1. `parcial/` arranca como **copia del TP Cap 1-4 entregado** (commit `e337710`: `app/`, `migrations/`, `test/`, `requirements.txt`, `alembic.ini`, `env.example`, `README.md`) y se **evoluciona incrementalmente ahí**. Nunca se rehace desde cero.
2. `despliegue/` es otra copia **congelada** del TP + Dockerfile (Ej. 9-10). No lleva ninguna modificación del parcial.
3. El código de la **raíz del repo queda como el TP original: no se toca**. Todo comando (pytest, alembic, uvicorn) del parcial se corre desde `parcial/`.
4. **C-01 crea ambas copias** antes de cualquier modificación.
5. **Strict TDD con pytest** en todos los changes (RED -> GREEN -> TRIANGULATE -> REFACTOR) contra PostgreSQL 16 descartable en Docker; además los `.http` y `solo_agregado.sql` que pide el PDF.
6. Ubicación de `main.py`: **`parcial/main.py` en la raíz**, junto a `seed.py`, como lo lista el PDF (DD-08); se revierte sólo si Q-03 dice otra cosa. `despliegue/` sigue con `app.main:app`.
8. **Capas en todos los módulos** (PDF p. 8-9): router construye el UoW con una dependencia, llama al servicio y traduce errores; el servicio recibe el UoW, lo abre con `async with` y **nunca recibe ni usa la sesión** ni hace commit/rollback; los repositorios hacen `flush()`, nunca `commit()`; el UoW base confirma/revierte al salir y no cierra la sesión. Única excepción: `intento_acceso` (sesión propia, DD-09). Ningún change puede dejar un servicio que toque `AsyncSession`.
7. El empaquetado final zipea `parcial/` + `despliegue/` tal como pide el PDF.

---

## Cómo usar este documento

1. Identificá el próximo change con `Estado: [ ]` cuyas dependencias estén todas `[x]` (ver árbol y GATES).
2. Leé los archivos de "Leer antes" de ese change en `knowledge-base/`.
3. Corré `/opsx:propose C-NN-<nombre>` (el scope de este documento es el punto de partida del proposal).
4. Implementá con `/opsx:apply` (Strict TDD) y cerrá con `/opsx:archive`.
5. Marcá el checkbox `Estado` como `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 snapshots-parcial-despliegue
├── C-02 test-infra-pytest-pg16
│   └── C-03 config-lifespan-health
│       ├── C-04 core-repo-uow-paginacion
│       │   └── C-05 modulos-referencia-refactor
│       ├── C-06 modelos-nuevos-migracion-0003
│       │   └── C-07 migracion-0004-solo-agregado
│       └── C-08 seguridad-bcrypt-jwt-core
│
│   C-09 usuarios-auth-endpoints        (C-04 + C-06 + C-08)
│   └── C-10 autorizacion-grupos-rutas
│       ├── C-11 roles-autoproteccion-eventos
│       ├── C-12 libros-stock-borrado-logico   (+ C-05, C-06)
│       └── C-13 clientes-uow-propios          (+ C-05, C-06)
│           └── C-14 ventas-transaccion-stock  (C-12 + C-13)
│               └── C-15 lecturas-sin-n1-paginacion
│                   ├── C-16 seed-py-datos-pdf         (+ C-11)
│                   │   ├── C-17 casos-http-evidencia  (+ C-15, C-07, C-11)
│                   │   └── C-18 readme-env-example-alembic
│
└── C-19 despliegue-ajustes-tp-congelado     (rama paralela, sólo despliegue/)
    └── C-20 dockerfile-imagen-alpine
        └── C-21 despliegue-vps-deploy-md    BLOQUEADO por Q-02

C-22 empaquetado-zip   (C-17 + C-18 + C-21)
```

### Paralelismo por fase

```
GATE 0: C-01 ✓                                   ← ambas copias creadas
  → C-02 test-infra-pytest-pg16                  [Agente A]
  → C-19 despliegue-ajustes-tp-congelado         [Agente C]  (sólo despliegue/, independiente del parcial)

GATE 1: C-02 ✓
  → C-03 config-lifespan-health                  [Agente A]

GATE 2: C-03 ✓                                   ← FORK
  → C-04 core-repo-uow-paginacion                [Agente A]
  → C-06 modelos-nuevos-migracion-0003           [Agente B]
  → C-08 seguridad-bcrypt-jwt-core               [Agente C]

GATE 3: C-04 ✓ → C-05 modulos-referencia-refactor   [Agente A]
        C-06 ✓ → C-07 migracion-0004-solo-agregado  [Agente B]
        C-04 + C-06 + C-08 ✓ → C-09 usuarios-auth-endpoints [Agente C]

GATE 4: C-09 ✓
  → C-10 autorizacion-grupos-rutas               [Agente C]

GATE 5: C-10 ✓                                   ← FORK
  → C-11 roles-autoproteccion-eventos            [Agente C]
  → C-12 libros-stock-borrado-logico             [Agente A — si C-05 ✓ y C-06 ✓]
  → C-13 clientes-uow-propios                    [Agente B — si C-05 ✓]

GATE 6: C-12 + C-13 ✓
  → C-14 ventas-transaccion-stock                [Agente A]

GATE 7: C-14 ✓
  → C-15 lecturas-sin-n1-paginacion              [Agente A]
  → C-16 seed-py-datos-pdf                       [Agente B — si C-11 ✓]

GATE 8: C-15 + C-16 ✓
  → C-17 casos-http-evidencia                    [Agente A — si C-07 ✓ y C-11 ✓]
  → C-18 readme-env-example-alembic              [Agente B]

GATE D (rama despliegue, independiente de GATE 1..8): C-19 ✓ → C-20 ✓ → C-21 (bloqueado por Q-02)

GATE FINAL: C-17 + C-18 + C-21 ✓
  → C-22 empaquetado-zip                         [Agente A]
```

> **Trabajo en paralelo**: los changes del parcial comparten `parcial/app/`; usar un git worktree por agente y mergear en orden de dependencias. Los de `despliegue/` no colisionan con nada.

### Camino crítico (11 changes — mínimo irreducible)

`C-01 -> C-02 -> C-03 -> C-06 -> C-09 -> C-10 -> C-12 -> C-14 -> C-15 -> C-17 -> C-22`

(C-04 y C-08 convergen en C-09 con la misma longitud que C-06. `C-21`* es co-final de C-22 pero fuera de la cadena del parcial: depende de Q-02.)

### Plan óptimo con 3 agentes

| Paso | Agente A (Parcial core) | Agente B (Modelos / dominio aux) | Agente C (Auth + Despliegue) |
|------|--------------------------|----------------------------------|------------------------------|
| 1 | C-01 snapshots-parcial-despliegue | — | — |
| 2 | C-02 test-infra-pytest-pg16 | — | C-19 despliegue-ajustes-tp-congelado |
| 3 | C-03 config-lifespan-health | — | C-20 dockerfile-imagen-alpine |
| 4 | C-04 core-repo-uow-paginacion | C-06 modelos-nuevos-migracion-0003 | C-08 seguridad-bcrypt-jwt-core |
| 5 | C-05 modulos-referencia-refactor | C-07 migracion-0004-solo-agregado | C-09 usuarios-auth-endpoints |
| 6 | — | — | C-10 autorizacion-grupos-rutas |
| 7 | C-12 libros-stock-borrado-logico | C-13 clientes-uow-propios | C-11 roles-autoproteccion-eventos |
| 8 | C-14 ventas-transaccion-stock | — | C-21 despliegue-vps-deploy-md (cuando llegue Q-02) |
| 9 | C-15 lecturas-sin-n1-paginacion | C-16 seed-py-datos-pdf | — |
| 10 | C-17 casos-http-evidencia | C-18 readme-env-example-alembic | — |
| 11 | C-22 empaquetado-zip | — | — |

---

## FASE 0 — Copias y base de pruebas

### [C-01] `snapshots-parcial-despliegue`
- **Estado**: `[x]` completo (2026-11-03; la herramienta de verificación `tools/`+`tests/` se usó y luego se eliminó a pedido del usuario)
- **Scope**:
  - Crear `parcial/` y `despliegue/` como copias idénticas del TP en `e337710` (`app/`, `migrations/`, `test/`, `requirements.txt`, `alembic.ini`, `env.example`, `README.md`) con `git archive`/`git show`; excluir `.venv`, `__pycache__`, `.env`, `.git`
  - Tag git `tp-cap1a4-entregado` sobre `e337710` como respaldo
  - Script de verificación (diff/hash) de que ambas copias son idénticas al commit y de que la raíz no cambió
  - Regla documentada: la raíz queda como el TP original; el parcial se desarrolla sólo en `parcial/`; `despliegue/` sólo lo toca la rama de despliegue
  - Tests: integridad de ambas copias vs `e337710`
- **Dependencias**: ninguna
- **Governance**: MEDIO (copia de código entregable; un error invalida Ej. 9-10 o la base del parcial)
- **Ejercicios / puntos**: habilita Ej. 1-10
- **Leer antes**:
  - `knowledge-base/09_decisiones_y_supuestos.md` (DD-03)
  - `knowledge-base/11_brecha_tp_vs_parcial.md` (nota inicial)
  - `knowledge-base/12_entregables_del_parcial.md` §Contenido del .zip

### [C-02] `test-infra-pytest-pg16`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - En `parcial/`: `pytest`, `pytest-asyncio`, `httpx` (AsyncClient + ASGITransport), `requirements-dev.txt`, `pytest.ini` (asyncio_mode)
  - PostgreSQL 16 descartable en Docker (sólo para tests; no es el Compose prohibido del Ej. 9), base `libreria_test`
  - `parcial/test/conftest.py`: engine de test, esquema **sólo con `alembic upgrade head`** (nunca `create_all`), limpieza por test con `TRUNCATE ... RESTART IDENTITY CASCADE` (el disparador de C-07 rechaza DELETE; DD-10), `AsyncClient` con lifespan
  - Helper para contar consultas SQL (usado por C-15); fixtures de usuarios/roles (stub hasta C-09)
  - Test de humo real (`GET /health/live` 200); `.env.test` fuera de git y del zip
- **Dependencias**: `C-01`
- **Governance**: BAJO
- **Ejercicios / puntos**: transversal (DD-01)
- **Leer antes**:
  - `knowledge-base/09_decisiones_y_supuestos.md` (DD-01)
  - `knowledge-base/12_entregables_del_parcial.md` §Verificación de invariantes
  - `knowledge-base/11_brecha_tp_vs_parcial.md` ("Tests pytest")

---

## FASE 1 — Configuración, ciclo de vida y capas core

### [C-03] `config-lifespan-health`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Reescribir `parcial/app/core/config.py` con `pydantic-settings`: `POSTGRES_USER/PASSWORD/DB/HOST/PORT` + URL `postgresql+asyncpg` con `@computed_field`, `SQL_ECHO`, clave de firma **y** `POSTGRES_PASSWORD` sin default (si faltan, no arranca; tampoco clave generada al arrancar), duración del token, costo bcrypt, pool, cookie `Secure` (nombres según Q-04); `.env` no versionado
  - `app/core/database.py`: funciones que crean motor (pool desde config, `echo=SQL_ECHO`) y fábrica (`expire_on_commit=False`) — **no se llaman al importar**; `get_session` toma la fábrica de `app.state`, entrega una sesión por petición y la cierra; sin commit/rollback
  - Mover `app/main.py` a `parcial/main.py` (DD-08): lifespan crea engine y factory y los guarda en `app.state`, calcula **una vez** el hash ficticio (stub hasta C-08), `engine.dispose()` al apagar; ningún recurso creado al importar; logger del aviso visible con uvicorn
  - `GET /health/live` no toca la base; `GET /health/ready` ejecuta `SELECT 1` -> 200 o **503** (IN-07); `health` sólo `router.py` (borrar `health/service.py`)
  - Actualizar `migrations/env.py` (usa `Settings`, sin credenciales en `alembic.ini`), `env.example` (todas las variables, ningún secreto), `requirements.txt` (`pydantic-settings`, sin `python-dotenv` si ya no se usa)
  - Tests: falla sin clave de firma y sin contraseña de base, URL computada, motor en `app.state` sólo tras el lifespan, `dispose()` al apagar, live sin base, 503 con base caída, sesión cerrada al terminar
- **Dependencias**: `C-02`
- **Governance**: ALTO (configuración y secretos)
- **Ejercicios / puntos**: Ej. 1 (6 pts)
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Variables de entorno y §Estructura
  - `knowledge-base/11_brecha_tp_vs_parcial.md` (Config, Motor/sesiones, Health)
  - `knowledge-base/10_preguntas_abiertas.md` (Q-04, IN-07)

### [C-04] `core-repo-uow-paginacion`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `app/core/repository.py`: **`BaseRepository[T]`** (constructor recibe la sesión **y la clase del modelo**; al menos `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`; `add`/`update` hacen `flush()`, nunca `commit()`) y **`SoftDeleteRepository[T]`** que hereda, filtra los dados de baja y agrega `get_by_id_including_deleted` y `soft_delete` (no existen en la base)
  - `app/core/unit_of_work.py`: `UnitOfWork` base, gestor de contexto async: commit al salir, rollback si sale con excepción, **no cierra la sesión**; patrón de UoW por módulo (compone repositorios con la misma sesión) y de dependencia del router que lo construye sin abrirlo
  - `app/core/paginacion.py`: `{items,total,page,size,pages}`, `page>=1`, `size` 1..100 (default 20), página más allá de la última 422 ("La página 4 no existe: hay 3"), `total` con los mismos filtros, una página vacía si total 0
  - Errores del dominio + traducción en el router (helper común): `IntegrityError` 23505/23503 -> 409 con mensaje propio, sin texto de la base; unicidad nunca verificada con consulta previa
  - Tests: commit al salir, rollback en excepción, la sesión sigue abierta tras el bloque, `flush` sin commit, `SoftDeleteRepository` filtra y `get_by_id_including_deleted` no, paginación (bordes), traducción de errores
- **Dependencias**: `C-03`
- **Governance**: MEDIO
- **Ejercicios / puntos**: Ej. 6 (parte), Ej. 3 (paginación)
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Capas, UoW y repositorios
  - `knowledge-base/05_reglas_de_negocio.md` §Paginación y §Errores
  - `knowledge-base/11_brecha_tp_vs_parcial.md` (Servicios, Listados, Errores)

### [C-05] `modulos-referencia-refactor`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Refactor de `editoriales`, `generos`, `autores` como patrón: `repository.py`, `unit_of_work.py`, `service.py` que recibe el UoW (sin `AsyncSession`, sin `commit`/`rollback`, sin `HTTPException`), `router.py` que construye el UoW y traduce errores; `models.py` sin cambios
  - `schemas.py`: contratos separados de los modelos de tabla, entradas con `extra="forbid"`, PATCH con `exclude_unset`, listados `GET /editoriales`, `/generos` con envoltorio
  - Endpoints del PDF: `GET /editoriales`, `/generos` (page, size) 200/422; `GET /{editoriales,generos,autores}/{id}/libros` 200/404; `POST` 201/409/422; `PATCH /editoriales/{id}`, `/autores/{id}` 200/404/409/422. Rutas sin barra final (IN-05); rutas extra del TP según Q-10
  - Tests: CRUD, 409 duplicado con mensaje propio, 404, 422 por extra, PATCH parcial, listado paginado
- **Dependencias**: `C-04`
- **Governance**: BAJO
- **Ejercicios / puntos**: Ej. 3 (parte), Ej. 6 (parte)
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Catálogo
  - `knowledge-base/08_arquitectura_propuesta.md` §Capas
  - `knowledge-base/11_brecha_tp_vs_parcial.md` (Contratos, Rutas)

---

## FASE 2 — Modelos y migraciones

> C-06 corre en paralelo con C-04 y C-08 (todos dependen sólo de C-03).

### [C-06] `modelos-nuevos-migracion-0003`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `app/modules/usuarios/models.py`: `Usuario` (`email` UNIQUE, `nombre`, `password_hash`, `activo`, `debe_cambiar_password`), `AsignacionRol` (`usuario_id`, `rol` con CHECK `IN ('ADMIN','VENDEDOR','CLIENTE')`, `desde`, `vence_en` nulo, `revocada_en` nulo, `otorgada_por` nulo [Q-17]; índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL`), `IntentoAcceso` (`cuando`, `email`, `ip`, `exito`; índice `(email, ip, cuando)`), `EventoSeguridad` (`cuando`, `actor` texto, `accion`; sin FK)
  - `app/modules/libros/models.py`: `MovimientoStock` (`libro_id`, `venta_id` nulo, `usuario_id` **NOT NULL** (Fig. 1: actor 1), `cantidad` con CHECK `<> 0`, `motivo`, `cuando`); `Libro.borrado_en` (timestamptz nulo) + índice único parcial de `isbn` (`postgresql_where=borrado_en IS NULL`) en lugar del UNIQUE; siguen CHECK `precio > 0` y `stock >= 0`
  - `app/modules/clientes/models.py`: `Cliente.usuario_id` (nulo, UNIQUE, FK) + `Cliente.usuario` que devuelve **un objeto** (`uselist=False`); `email` sigue UNIQUE
  - Todas las fechas nuevas `timestamptz`; dinero sigue `NUMERIC`/`Decimal`; nulo sólo donde el PDF dice "(nulo)"; **índice en cada FK nueva** (`asignacion_rol.usuario_id`, `otorgada_por` si es FK, `movimiento_stock.libro_id/venta_id/usuario_id`); relaciones con `back_populates` en los dos extremos (`Usuario.asignaciones`, `Usuario.cliente`, `Usuario.movimientos`, `Libro.movimientos`, `Venta.movimientos`); `editorial`, `genero`, `autor`, `libro_autor`, `perfil_cliente`, `venta`, `renglon_venta` no cambian
  - Migración **0003** con `alembic revision --autogenerate`, **leída antes de aplicar** y con comentario que lo diga; corregida a mano donde haga falta (comentario que lo explique): dropear `uq_libro_isbn` (nombre real en 0001), crear `ix_libro_isbn_vigente`, quitar drops/creates espurios por UNIQUE sin nombre en los modelos; downgrade completo
  - Registrar modelos en `app/modules/models.py`; decidir backfill "Stock inicial" (Q-08)
  - Tests: upgrade/downgrade sobre base vacía, cada CHECK, columnas NOT NULL/nulas, índices de FK presentes (`pg_indexes`), único parcial (ISBN repetido vigente rechazado / tras baja permitido; segunda asignación abierta del mismo rol rechazada), `Cliente.usuario` es objeto, relaciones navegables en ambos extremos
- **Dependencias**: `C-03`
- **Governance**: ALTO (migraciones y esquema de datos)
- **Ejercicios / puntos**: Ej. 2 (10 pts)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md`
  - `knowledge-base/11_brecha_tp_vs_parcial.md` §Detalle de riesgos de la migración
  - `knowledge-base/10_preguntas_abiertas.md` (IN-01, Q-08, Q-09)

### [C-07] `migracion-0004-solo-agregado`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Migración **0004 escrita a mano** (comentario: la comparación automática no ve funciones ni disparadores): función + disparador en `movimiento_stock` que rechaza UPDATE y DELETE "venga de donde venga" (RN-12); downgrade los elimina; TRUNCATE no se bloquea (DD-10)
  - `parcial/test/solo_agregado.sql` (caso C-14)
  - Tests: UPDATE/DELETE desde SQL directo rechazados, INSERT permitido, ciclo completo **`upgrade head` (base vacía) -> `downgrade base` -> `upgrade head`** con 0001..0004
- **Dependencias**: `C-06`
- **Governance**: ALTO (integridad de auditoría, DDL a mano)
- **Ejercicios / puntos**: Ej. 2 (parte), Ej. 7 (10 pts)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §movimiento_stock
  - `knowledge-base/05_reglas_de_negocio.md` §Sólo agregado
  - `knowledge-base/12_entregables_del_parcial.md` (caso C-14)

---

## FASE 3 — Autenticación y autorización

### [C-08] `seguridad-bcrypt-jwt-core`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `app/core/security.py`: **toda** llamada a bcrypt vía `asyncio.to_thread` bajo un semáforo que limita cuántas corren a la vez, costo desde `Settings`, rechazo > 72 bytes (bytes, no caracteres), hash ficticio real calculado una vez en el lifespan
  - JWT (PyJWT) firmado con la clave de `Settings`, con `sub`, `exp` y roles vigentes al emitirlo; cookie **`access_token`** `HttpOnly`, `SameSite=Lax`, `Max-Age` = duración del token, `Secure` configurable; nunca en el cuerpo
  - Tests: verify ok/falso, 72 bytes ("ñ" cuenta 2), el event loop no se bloquea, semáforo limita concurrencia, expiración, firma inválida, claims `sub`/`exp`/roles
- **Dependencias**: `C-03`
- **Governance**: CRITICO (credenciales y tokens)
- **Ejercicios / puntos**: Ej. 4 (parte)
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §Auth
  - `knowledge-base/03_actores_y_roles.md`
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/10_preguntas_abiertas.md` (Q-04)

### [C-09] `usuarios-auth-endpoints`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Módulo `usuarios` completo: `models.py` (de C-06), `schemas.py`, `repository.py` (uno por entidad: usuario, asignación, intento, evento), `unit_of_work.py`, `service.py` (recibe el UoW), `router.py` (construye el UoW y traduce errores)
  - Contratos: `extra="forbid"` (nadie se registra con un rol), contraseñas de registro, login, actual y nueva <= 72 bytes -> 422; ninguna respuesta con `password_hash`
  - `POST /auth/registro` (201/409/422): hash **antes** de abrir el UoW; usuario + rol CLIENTE + ficha de cliente en **un solo bloque**; correo repetido de usuario o de cliente -> 409 por el UNIQUE (sin consulta previa), sin apropiarse de la ficha ni dejar filas sueltas (Q-09)
  - `POST /auth/login` (200/401/422/429): (1) conteo en `intento_acceso` de fallos (email, ip) en 60 s posteriores al último login correcto -> 429 + `Retry-After` sin calcular hash; (2) verificación contra el hash del usuario o el **hash ficticio**; 401 con el mismo cuerpo y tiempo parecido; cuerpo `{mensaje, debe_cambiar_password, expira_en_segundos}` sin token; cookie `access_token`
  - `POST /auth/logout` (200, borra la cookie), `GET /auth/yo` (usuario, roles vigentes y roles del token), `POST /auth/cambiar-password` (200/401/422; hash nuevo antes del UoW; en un solo bloque contraseña + `debe_cambiar_password=false` + línea en `evento_seguridad` (RN-16); no emite token ni invalida sesiones; Q-11 para contraseña actual errónea)
  - `intento_acceso` (correcto o fallido) en su **propia sesión y transacción, siempre confirmadas**, vía UoW propio (DD-09), con el comentario de tres puntos (qué hace distinto, por qué, costo); Q-20
  - Tests (C-02 a C-05): registro y atomicidad, cookie y flags, 401 uniforme, 429 al 6.º en pocos ms, login correcto reinicia la cuenta, intentos persisten tras 401, evento del cambio de contraseña
- **Dependencias**: `C-04`, `C-06`, `C-08`
- **Governance**: CRITICO (autenticación)
- **Ejercicios / puntos**: Ej. 4 (14 pts), Ej. 7 (intento de acceso)
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §Auth y §Límite de intentos
  - `knowledge-base/07_flujos_principales.md` §Registro y login
  - `knowledge-base/04_modelo_de_datos.md` §usuario, intento_acceso
  - `knowledge-base/10_preguntas_abiertas.md` (Q-05, Q-09, Q-11)

### [C-10] `autorizacion-grupos-rutas`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `app/core/dependencies.py`: `get_usuario_actual` (401 sin cookie, token inválido o vencido, usuario inexistente o **inactivo**; lee sólo `request.cookies`, `Authorization: Bearer` -> 401), roles vigentes (no revocados y sin vencer), control del cambio obligatorio, `requiere_rol` (403; roles leídos de `asignacion_rol` en cada petición, los del token son informativos); todas reciben **la misma sesión que el UoW** de la petición
  - Dos grupos de rutas en `main.py`: **abierto** (health, `/auth/*` incluidos `/auth/yo` y `/auth/cambiar-password`, catálogo público) y **protegido** con el control del cambio obligatorio montado **una sola vez**; matriz de permisos del PDF (`03_actores_y_roles.md`) aplicada a los routers existentes
  - Cambio de contraseña obligatorio: 403 en el grupo protegido; la misma cookie sirve tras el cambio
  - Tests (C-01, C-06, C-09): 422 por parámetro no entero con sesión, 401 vs 403, usuario inactivo 401, rol revocado se aplica en la petición siguiente, bloqueo por cambio obligatorio, una sola conexión por petición autenticada
- **Dependencias**: `C-09`
- **Governance**: CRITICO (autorización)
- **Ejercicios / puntos**: Ej. 5 (12 pts)
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` (matriz de permisos)
  - `knowledge-base/05_reglas_de_negocio.md` §Autorización
  - `knowledge-base/06_funcionalidades.md`
  - `knowledge-base/10_preguntas_abiertas.md` (Q-12)

### [C-11] `roles-autoproteccion-eventos`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `POST /usuarios` (ADMIN; 201/409/422): alta de personal con contraseña provisoria (hash antes del UoW), `debe_cambiar_password=true`, rol inicial y línea en `evento_seguridad`, en un solo bloque; correo repetido 409
  - `GET /usuarios/{id}/roles` (200/404), `POST /usuarios/{id}/roles` (201/404/409/422; `vence_en` opcional, con zona y futuro, si no 422), `DELETE /usuarios/{id}/roles/{rol}` (200/404/409; escribe `revocada_en`, **nunca borra** la fila)
  - RN-03: una asignación abierta por rol -> 409 por el índice único parcial; **reasignar un rol vencido cierra la fila anterior y abre una nueva**
  - RN-05: el administrador no puede revocarse su ADMIN y el sistema **nunca queda sin administradores vigentes** -> 409 (comprobación en el servicio)
  - RN-16: cada alta de personal, cambio de rol (asignar y revocar) deja su línea en `evento_seguridad` **en la misma transacción**; actor `SISTEMA` (texto) para los datos iniciales
  - `GET /eventos` (ADMIN; page, size; 200/422) con el envoltorio de paginación
  - Tests (C-07, C-08): revocación con sesión abierta (403 siguiente; `/auth/yo` muestra la diferencia; fila revocada sigue), vencimientos 422, segunda asignación abierta 409, reasignación de vencido, autoprotección, último admin, atomicidad del evento (si falla el evento no queda el cambio)
- **Dependencias**: `C-10`
- **Governance**: CRITICO (roles y auditoría de seguridad)
- **Ejercicios / puntos**: Ej. 5 (parte), Ej. 7 (eventos)
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md`
  - `knowledge-base/05_reglas_de_negocio.md` §Roles y §Eventos de seguridad
  - `knowledge-base/04_modelo_de_datos.md` §asignacion_rol, evento_seguridad
  - `knowledge-base/10_preguntas_abiertas.md` (Q-05)

---

## FASE 4 — Dominio: libros, clientes, ventas, lecturas

> C-12 y C-13 son paralelos entre sí.

### [C-12] `libros-stock-borrado-logico`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Módulo `libros` con `repository.py` (libro sobre `SoftDeleteRepository`, `LibroAutor`, `MovimientoStock`), `unit_of_work.py`, `service.py` (recibe el UoW), `router.py`, `schemas.py`
  - `POST /libros` (ADMIN; 201/409/422) con `autores` y `stock_inicial` (no `stock`): libro + autorías + movimiento "Stock inicial" en un solo bloque; `PATCH /libros/{id}` (200/404/409/422) sólo título y precio (`stock` -> 422 por `extra="forbid"`); `DELETE /libros/{id}` (204/404) baja lógica; `POST /libros/{id}/reponer` (200/404/409/422; libro dado de baja -> 409); `GET /libros/{id}/movimientos` (ADMIN; 200/404) (Q-18)
  - **Punto único de escritura de stock** (repositorio/servicio de stock que usan alta, reposición y ventas): actualiza `libro.stock` y agrega el movimiento con `usuario_id` del actor; `stock == SUM(movimientos)`
  - Catálogo público sin dados de baja: `GET /libros` (page, size, `titulo` ILIKE con parámetros ligados, `genero_id`), `GET /libros/{id}` (404 si dado de baja, Q-19) y los listados `/{editoriales,generos,autores}/{id}/libros`
  - Reuso de ISBN tras la baja (201); segundo vigente 409
  - Permisos por rol (vendedor no crea libros 403)
  - Tests (C-13, C-16 parte): reposición, baja, desaparece del catálogo, ISBN, PATCH stock 422, reponer dado de baja 409, movimientos, invariante
- **Dependencias**: `C-05`, `C-06`, `C-10`
- **Governance**: MEDIO
- **Ejercicios / puntos**: Ej. 3 (parte), Ej. 6 (parte)
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §Stock y §Borrado lógico
  - `knowledge-base/07_flujos_principales.md` §Reposición y baja
  - `knowledge-base/04_modelo_de_datos.md` §libro, movimiento_stock
  - `knowledge-base/10_preguntas_abiertas.md` (Q-07, Q-08)

### [C-13] `clientes-uow-propios`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Refactor de `clientes` y `perfil` (1-1): `repository.py` (cliente, perfil), `unit_of_work.py`, `service.py` que recibe el UoW, `router.py`, `schemas.py` con `extra="forbid"`; `Cliente.usuario`
  - Endpoints (VENDEDOR, ADMIN): `POST /clientes` (201/409/422), `GET`/`PATCH /clientes/{id}` con su perfil (200/404/409/422), `POST /clientes/{id}/perfil` (201/404/409), `GET /clientes/{id}/ventas` (200/404); 409 por correo vía UNIQUE
  - `GET /clientes` paginado sólo si Q-10 lo conserva; base para `/mis-ventas`
  - Tests: CRUD, 409 correo, 404, 422, segundo perfil 409, vínculo usuario-cliente, cliente 403 en estas rutas
- **Dependencias**: `C-05`, `C-06`, `C-10`
- **Governance**: MEDIO
- **Ejercicios / puntos**: Ej. 3 (parte), Ej. 5 (lo propio), Ej. 6 (parte)
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §cliente, perfil
  - `knowledge-base/06_funcionalidades.md` §Clientes
  - `knowledge-base/03_actores_y_roles.md`
  - `knowledge-base/10_preguntas_abiertas.md` (Q-09, Q-10)

### [C-14] `ventas-transaccion-stock`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Módulo `ventas` con `repository.py` (venta, renglón), `unit_of_work.py` (compone repositorios de ventas, clientes y libros/stock con la misma sesión), `service.py` (recibe el UoW), `router.py`, `schemas.py`
  - Contrato (RN-09): `cliente_id` + `renglones` (al menos uno, sin libros repetidos, `cantidad > 0`) -> si no 422; precio, total y fecha no viajan (`extra="forbid"`); no hay PATCH de ventas
  - `POST /ventas` (VENDEDOR, ADMIN; 201/409/422) en **un solo bloque**: venta + renglones (precio copiado, total del servidor) + descuento por el punto único de stock + un `movimiento_stock` por renglón (cantidad negativa, `venta_id`, `usuario_id` del vendedor); el servicio nunca commitea
  - 409 sin escrituras si no alcanza el stock, o cliente/libro inexistente o dado de baja; rollback total
  - Aviso `BackgroundTasks` (`await asyncio.sleep(0.5)` + mensaje en el registro) sólo si confirmó, visible en el log de uvicorn tras la respuesta
  - `GET /ventas` (VENDEDOR, ADMIN; page, size; 200/422); `GET /ventas/{id}` **sin `requiere_rol`**: el servicio decide (personal o cliente dueño; si no 403; 404); `GET /mis-ventas` (autenticado; page, size; 200/422)
  - Tests (C-10, C-11, C-12): venta válida, Rayuela+Bestiario 409 con invariantes, tres 409, stock == SUM, aviso sólo tras commit
- **Dependencias**: `C-12`, `C-13`
- **Governance**: ALTO (transacción y consistencia de stock)
- **Ejercicios / puntos**: Ej. 6 (núcleo, 16 pts), Ej. 8 (aviso), Ej. 5 (dueño)
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §Ventas y §Stock
  - `knowledge-base/07_flujos_principales.md` §Venta
  - `knowledge-base/08_arquitectura_propuesta.md` §Unit of Work
  - `knowledge-base/12_entregables_del_parcial.md` §Verificación de invariantes

### [C-15] `lecturas-sin-n1-paginacion`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Precarga dentro del método del repositorio; detalle de venta con cantidad fija de consultas (2 vs 4 renglones) e incluye libro dado de baja
  - Todos los listados con paginación y `total` con los mismos filtros; búsqueda segura (`' OR '1'='1` total 0)
  - Revisión final de contratos: sin `password_hash`, `extra="forbid"` en entradas, ningún 500 por entrada inválida (incluidos ids fuera de `int4`), ningún texto de la base en errores, todos los handlers `async def` sin llamadas bloqueantes, ninguna lectura por carga perezosa
  - Auditoría de capas: `grep` de `AsyncSession`/`commit(` en `service.py` y `router.py` de todos los módulos debe dar vacío (salvo DD-09)
  - Tests (C-15, C-16): conteo de consultas igual con 2 y 4 renglones (con libro dado de baja), `titulo=ficc&size=1` total 1 pages 1 y `page=2` 422, `size=500` 422, `' OR '1'='1` total 0, id gigante 422/404 (no 500)
- **Dependencias**: `C-14`
- **Governance**: MEDIO
- **Ejercicios / puntos**: Ej. 8 (6 pts), Ej. 3 (cierre)
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §Lecturas y §Paginación
  - `knowledge-base/07_flujos_principales.md` §Detalle de venta
  - `knowledge-base/11_brecha_tp_vs_parcial.md` (Lecturas, Contratos, Listados)

---

## FASE 5 — Datos, casos y documentación del parcial

### [C-16] `seed-py-datos-pdf`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `parcial/seed.py` (raíz, DD-08): vacía tablas con `TRUNCATE ... RESTART IDENTITY CASCADE` (DD-10) y carga datos del PDF (3 editoriales, 3 géneros, 6 autores, 5 libros en el orden y con precios/stock según IN-02/IN-03, clientes Lucía con perfil y Tomás sin usuario, Ana Paz con `ana@example.com`, usuarios admin, admin2, vendedor, ana, nuevo con contraseñas de mentira Q-05 y `nuevo` con cambio obligatorio), venta 1 de Lucía (1 Rayuela + 2 Ficciones = 69000.00) registrada por vendedor, movimientos "Stock inicial" (Rayuela 11, Ficciones 10) y las dos salidas (-1, -2) con su `usuario_id` (Q-08), línea `SISTEMA` "Carga de los datos iniciales"
  - Decidir si se retira `test/seed.sql`
  - Tests: seed idempotente, `stock == SUM(movimientos)` en los cinco libros, roles correctos
- **Dependencias**: `C-14`, `C-11`
- **Governance**: MEDIO
- **Ejercicios / puntos**: soporte de casos C y README
- **Leer antes**:
  - `knowledge-base/10_preguntas_abiertas.md` (IN-02, IN-03, Q-05, Q-07, Q-08)
  - `knowledge-base/07_flujos_principales.md` §Seed
  - `knowledge-base/04_modelo_de_datos.md`

### [C-17] `casos-http-evidencia`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `parcial/test/*.http` como `C-01..C-16` (IN-04) con respuesta esperada en comentario, sesiones múltiples (`# @name`, `# @no-cookie-jar`, `Cookie:`), precedidos de `python seed.py`
  - `solo_agregado.sql` verificado; `parcial/evidencia/`: consultas del detalle con 2 y 4 renglones (`SQL_ECHO=true`) y captura de psql de C-14
  - Verificación manual contra uvicorn real
- **Dependencias**: `C-15`, `C-16`, `C-07`, `C-11`
- **Governance**: BAJO
- **Ejercicios / puntos**: evidencia de Ej. 3-8
- **Leer antes**:
  - `knowledge-base/12_entregables_del_parcial.md` §Casos de prueba: C
  - `knowledge-base/07_flujos_principales.md`
  - `knowledge-base/10_preguntas_abiertas.md` (IN-04, IN-05)

### [C-18] `readme-env-example-alembic`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `parcial/README.md`: integrantes (Q-06), venv, dependencias, `.env` + cómo generar la clave de firma, `alembic upgrade head`, `python seed.py`, arranque
  - `env.example` completo sin secretos; `alembic.ini` sin credenciales
  - Verificación desde cero (venv limpio + base vacía) siguiendo el README (regla dura)
  - Tests: `env.example` cubre todos los campos de `Settings`; sin secretos
- **Dependencias**: `C-16`
- **Governance**: BAJO
- **Ejercicios / puntos**: requisito de entrega
- **Leer antes**:
  - `knowledge-base/12_entregables_del_parcial.md` §README.md y §Reglas duras
  - `knowledge-base/08_arquitectura_propuesta.md` §Variables de entorno
  - `knowledge-base/10_preguntas_abiertas.md` (Q-06)

---

## FASE 6 — Despliegue del TP Cap 1-4 (rama paralela, sólo `despliegue/`)

> Puede correr en paralelo con las fases 1-5 una vez hecho C-01.

### [C-19] `despliegue-ajustes-tp-congelado`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Corregir en `despliegue/` sólo defectos propios: IN-07 (`/health/ready` 503) e IN-06 (cargar datos iniciales en Alpine sin `psql`); actualizar README del TP congelado
  - Lista de cambios para DEPLOY.md; la lógica de ventas queda intacta
  - Tests pytest sobre `despliegue/` (health 503)
- **Dependencias**: `C-01`
- **Governance**: MEDIO
- **Ejercicios / puntos**: Ej. 9-10 (parte)
- **Leer antes**:
  - `knowledge-base/10_preguntas_abiertas.md` (IN-05, IN-06, IN-07)
  - `knowledge-base/12_entregables_del_parcial.md` §Dockerfile
  - `knowledge-base/09_decisiones_y_supuestos.md`

### [C-20] `dockerfile-imagen-alpine`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - `despliegue/Dockerfile`: `FROM python:3.12-alpine`, `requirements.txt` antes del código con `--no-cache-dir`, usuario sin privilegios + `USER`, arranque `alembic upgrade head` y `uvicorn app.main:app --host 0.0.0.0` (8000), `HEALTHCHECK` con `wget http://127.0.0.1:8000/health/ready`; sin Compose
  - `.dockerignore` (`.env`, `.venv`, `.git`, `__pycache__`), `despliegue/env.example`
  - Arranque encadenado (`alembic upgrade head && exec uvicorn ...`): si la base no responde, el contenedor termina con error (D-05)
  - Verificación local de D-01, D-02, D-04, D-05, D-06, D-07; guardar salida
  - Tests: build, **imagen base** `python:3.12-alpine` < 100 MB (la del proyecto puede ser mayor), usuario no root, sin `.env` ni secretos (`ls -a /app`, `env`), estado `healthy`
- **Dependencias**: `C-19`
- **Governance**: ALTO (secretos en imagen)
- **Ejercicios / puntos**: Ej. 9 (11 pts)
- **Leer antes**:
  - `knowledge-base/12_entregables_del_parcial.md` §Dockerfile y §Casos D
  - `knowledge-base/07_flujos_principales.md` §Flujo 7 (despliegue)
  - `knowledge-base/10_preguntas_abiertas.md` (Q-02)

### [C-21] `despliegue-vps-deploy-md`
- **Estado**: `[ ]` pendiente — BLOQUEADO por Q-02 (datos del VPS, puerto, URL pública, base de la cátedra)
- **Scope**:
  - Despliegue en el VPS (build en servidor o imagen transferida) con `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file <archivo> libreria` (`--add-host=host.docker.internal:host-gateway` si corresponde)
  - Datos iniciales con el comando definido en C-19
  - `despliegue/DEPLOY.md`: URL, día y hora, comandos completos, cambios al TP, actualización, build vs imagen
  - `despliegue/evidencia/` con salida de D-01..D-08 (Q-14)
- **Dependencias**: `C-20` y respuesta de Q-02
- **Governance**: ALTO (despliegue con secretos y base real)
- **Ejercicios / puntos**: Ej. 10 (7 pts)
- **Leer antes**:
  - `knowledge-base/12_entregables_del_parcial.md` §DEPLOY.md y §Casos D
  - `knowledge-base/10_preguntas_abiertas.md` (Q-02, Q-14)
  - `knowledge-base/07_flujos_principales.md` §Flujo 7 (despliegue)

---

## FASE 7 — Empaquetado

### [C-22] `empaquetado-zip`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Script reproducible que genera `Parcial_Cap1a6_<Grupo>.zip` (Q-01) con `parcial/` + `despliegue/` tal como pide el PDF
  - Exclusiones: `.venv`, `__pycache__` (ambas carpetas), `.env`, `.env.test`, `.pytest_cache`, `.git` salvo decisión (Q-15); fuera del zip: raíz del TP original, `knowledge-base/`, `openspec/`, `CHANGES.md`, `.claude/`, PDFs de consigna
  - Verificación: árbol idéntico al del PDF; búsqueda de secretos; `alembic upgrade head` y `python seed.py` desde el zip extraído en directorio limpio
  - Tests: pytest que inspecciona el zip (presencia/ausencia de rutas)
- **Dependencias**: `C-17`, `C-18`, `C-21`
- **Governance**: ALTO (riesgo de filtrar credenciales: regla dura del PDF)
- **Ejercicios / puntos**: requisito de entrega (100 pts)
- **Leer antes**:
  - `knowledge-base/12_entregables_del_parcial.md` §Contenido del .zip y §Reglas duras
  - `knowledge-base/10_preguntas_abiertas.md` (Q-01, Q-13, Q-15)
  - `knowledge-base/09_decisiones_y_supuestos.md`

---

## Resumen

| ID | Change | Ej. / pts | Governance | Depende de |
|----|--------|-----------|------------|------------|
| C-01 | snapshots-parcial-despliegue | habilita todo | MEDIO | — |
| C-02 | test-infra-pytest-pg16 | transversal | BAJO | C-01 |
| C-03 | config-lifespan-health | Ej.1 (6) | ALTO | C-02 |
| C-04 | core-repo-uow-paginacion | Ej.6/3 | MEDIO | C-03 |
| C-05 | modulos-referencia-refactor | Ej.3/6 | BAJO | C-04 |
| C-06 | modelos-nuevos-migracion-0003 | Ej.2 (10) | ALTO | C-03 |
| C-07 | migracion-0004-solo-agregado | Ej.2/7 | ALTO | C-06 |
| C-08 | seguridad-bcrypt-jwt-core | Ej.4 | CRITICO | C-03 |
| C-09 | usuarios-auth-endpoints | Ej.4 (14), Ej.7 | CRITICO | C-04, C-06, C-08 |
| C-10 | autorizacion-grupos-rutas | Ej.5 (12) | CRITICO | C-09 |
| C-11 | roles-autoproteccion-eventos | Ej.5/7 | CRITICO | C-10 |
| C-12 | libros-stock-borrado-logico | Ej.3/6 | MEDIO | C-05, C-06, C-10 |
| C-13 | clientes-uow-propios | Ej.3/5/6 | MEDIO | C-05, C-06, C-10 |
| C-14 | ventas-transaccion-stock | Ej.6 (16), Ej.8 | ALTO | C-12, C-13 |
| C-15 | lecturas-sin-n1-paginacion | Ej.8 (6) | MEDIO | C-14 |
| C-16 | seed-py-datos-pdf | soporte | MEDIO | C-14, C-11 |
| C-17 | casos-http-evidencia | Ej.3-8 | BAJO | C-15, C-16, C-07, C-11 |
| C-18 | readme-env-example-alembic | entrega | BAJO | C-16 |
| C-19 | despliegue-ajustes-tp-congelado | Ej.9-10 | MEDIO | C-01 |
| C-20 | dockerfile-imagen-alpine | Ej.9 (11) | ALTO | C-19 |
| C-21 | despliegue-vps-deploy-md | Ej.10 (7) | ALTO | C-20 (+ Q-02) |
| C-22 | empaquetado-zip | entrega | ALTO | C-17, C-18, C-21 |

**Primer change recomendado**: `C-01` (`snapshots-parcial-despliegue`) -> `/opsx:propose C-01-snapshots-parcial-despliegue`
