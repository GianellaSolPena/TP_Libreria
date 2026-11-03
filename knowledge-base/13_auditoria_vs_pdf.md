# Auditoría KB + CHANGES.md vs. `Parcial_Cap1a6_Consigna.pdf`

Fecha: 2026-11-03. Autoridad: el PDF (24 p.). Método:
- Texto re-extraído con `pdftotext -table` (xpdf 4.06), que respeta las columnas. Así se verificaron fila por fila las tablas que la extracción `-layout` original había intercalado: modelo (p. 5-6), RN-01..RN-16 con su garante (p. 7-8), estructura obligatoria (p. 8-9), endpoints (p. 16-18), datos iniciales (p. 19-20), requisitos no funcionales (p. 20-21) y casos C/D (p. 21-23).
- La **Figura 1** (p. 5) se leyó renderizando la página a imagen (pypdfium2): composición, agregación, asociaciones y multiplicidades.
- Brecha contra el código real del TP (`app/modules/*/models.py`, `migrations/versions/0001`, `0002`, `test/seed.sql`, routers y servicios).

Leyenda: ✅ completo y correcto · ⚠️ parcial, impreciso o sólo implícito · ❌ ausente o erróneo. "Antes" = estado previo a esta auditoría; "Después" de cada fila es ✅ salvo que se marque **(Q-xx)**: en ese caso queda una pregunta abierta en `10_preguntas_abiertas.md`.

## Resultado del emparejamiento de tablas
- **RN ↔ garante**: las 16 coincidían ya con el PDF (la reconstrucción previa era correcta). Sólo se reemplazó la nota de "reconstrucción" por "verificada".
- **Endpoints**: las 33 filas (grupo, método, ruta, quién, códigos) coincidían en `06_funcionalidades.md`. Errores encontrados *fuera* de la tabla: `CHANGES.md` C-09 decía `GET /auth/logout` (el PDF dice **POST**); Q-11 y Q-12 preguntaban cosas que el PDF sí responde (`GET /ventas` = VENDEDOR, ADMIN; logout POST, "Cualquiera", 200; cambiar-password en grupo abierto, "Autenticado", 200/401/422).
- **Modelo**: columnas y restricciones correctas; faltaban nulabilidad, tipos, índices por FK, relaciones de la Fig. 1 y el nombre real del UNIQUE del ISBN (`uq_libro_isbn`, no `libro_isbn_key`).

## Matriz

### A. Objetivos, alcance y "qué cambia" (p. 1-3)
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| A01 | Capas Router → Service → UoW → Repository → Model, cada capa sabe lo suyo | 1 | ⚠️ | ⚠️ | Tabla de responsabilidades por capa (hace / no hace); premisa 8 de CHANGES; archivos por capa en cada módulo | 08 §Responsabilidades; CHANGES premisa 8, C-05, C-09, C-12, C-13, C-14 |
| A02 | Migración autogenerada y leída + otra a mano | 1, 10 | ✅ | ✅ | — | 04, C-06, C-07 |
| A03 | bcrypt + token en cookie HttpOnly, sin frenar el servidor ni revelar cuentas | 1, 11 | ✅ | ✅ | — | 05, C-08, C-09 |
| A04 | Roles en la base por petición, con vigencia; 401 vs 403 | 1, 11 | ✅ | ⚠️ | C-10: usuario inactivo 401, misma sesión | C-10 |
| A05 | Una transacción por operación de negocio | 1, 12 | ✅ | ✅ | — | C-09, C-11, C-14 |
| A06 | Delegar en la base: unicidad entre vigentes, FKs, CHECKs, sólo agregado | 1 | ⚠️ | ⚠️ | "Unicidad sin consulta previa" explícita; 409 desde `IntegrityError` | 05 §Manejo de errores; C-04, C-09 |
| A07 | Docker del TP Cap 1-4 sin filtrar secretos | 1, 14 | ✅ | ✅ | — | 12, C-20 |
| A08 | Fuera de alcance: concurrencia (cap. 7), Redis (cap. 8), 2.º mecanismo sólo agregado | 2, 12 | ✅ | — | — | 01 |
| A09 | Tabla "qué cambia": stock no por PATCH, listados con envoltorio, Settings, capas | 2 | ✅ | ✅ | — | 11 |

### B. Requisitos técnicos y configuración (p. 3-4, Ej. 1)
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| B01 | Versiones mínimas (Py 3.12, FastAPI 0.111, SQLModel 0.0.24, SA 2.0, asyncpg 0.30, PG 16, Alembic 1.13, pydantic-settings 2.0, bcrypt 4.0, PyJWT 2.8, Docker 20.10) | 3-4 | ✅ | ⚠️ | Deps faltantes en `requirements.txt` listadas | 11 (fila requirements); C-03, C-08 |
| B02 | `Settings` (pydantic-settings) desde entorno o `.env` no versionado | 4 | ✅ | ✅ | — | 08; C-03 |
| B03 | URL armada con `POSTGRES_USER/PASSWORD/DB/HOST/PORT` y driver `postgresql+asyncpg` con `@computed_field` | 4, 9 | ✅ | ⚠️ | Variables y driver explícitos en C-03 | C-03 |
| B04 | Clave de firma **y contraseña de la base** sin default; si faltan no arranca; tampoco clave inventada al arrancar | 4 | ⚠️ | ⚠️ | Agregada la contraseña de base y la prohibición de clave generada | 05 §Excepciones; C-03 |
| B05 | `env.example` con todas las variables, ningún secreto | 4 | ✅ | ✅ | — | C-03, C-18 |
| B06 | Motor con tamaño de pool en la config; motor y fábrica creados en el lifespan y guardados en `app.state`, no al importar | 9 | ✅ | ⚠️ | C-03 detalla "no se llaman al importar" y tests de `app.state` | C-03 |
| B07 | `get_session` toma la fábrica de `app.state`, una sesión por petición, `expire_on_commit=False`, la cierra | 9 | ✅ | ⚠️ | Explícito en C-03 | C-03 |
| B08 | Hash ficticio calculado una vez en el lifespan; `dispose()` al apagar | 9 | ✅ | ✅ | — | C-03, C-08 |
| B09 | `/health/live` no toca la base; `/health/ready` `SELECT 1`, 503 si no contesta | 9 | ✅ | ⚠️ | Tests de live sin base agregados | C-03 |
| B10 | `main.py` (raíz) con aplicación, lifespan y los dos grupos de rutas | 8 | ⚠️ | ⚠️ | DD-08: `parcial/main.py` en la raíz por letra del PDF; C-03 lo mueve **(Q-03 para confirmar)** | 08, 09 DD-08, 10 Q-03; CHANGES premisa 6, C-03 |

### C. Modelo de dominio (p. 4-6, Fig. 1, Ej. 2)
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| C01 | Nombres de tablas/columnas obligatorios; se puede agregar, no quitar ni renombrar | 4 | ✅ | — | — | 04 |
| C02 | `editorial`, `genero`, `autor`, `libro_autor`, `perfil_cliente` no cambian; `venta`/`renglon_venta` en gris en la Fig. 1 | 4-5 | ⚠️ | ⚠️ | Lista con nombres reales de restricciones de 0001/0002; venta/renglón marcados sin cambios | 04; C-06 |
| C03 | `usuario(id, email UNIQUE, nombre, password_hash, activo, debe_cambiar_password)` | 5 | ✅ | ⚠️ | Columnas explícitas en C-06 | 04; C-06 |
| C04 | `asignacion_rol(id, usuario_id, rol, desde, vence_en nulo, revocada_en nulo, otorgada_por nulo)`; CHECK rol IN (ADMIN, VENDEDOR, CLIENTE); índice único parcial (usuario_id, rol) WHERE revocada_en IS NULL | 5 | ✅ | ⚠️ | CHECK e índice parcial explícitos en C-06; relación de `otorgada_por` no dibujada **(Q-17)** | 04; C-06; 10 Q-17 |
| C05 | `intento_acceso(id, cuando, email, ip, exito)` + índice (email, ip, cuando) | 5 | ✅ | ❌ | Índice compuesto agregado a C-06 | C-06 |
| C06 | `evento_seguridad(id, cuando, actor texto, accion)`, sin restricciones ni relaciones | 5 | ✅ | ⚠️ | "sin FK" explícito | 04; C-06 |
| C07 | `cliente.usuario_id` nulo + UNIQUE; `email` sigue UNIQUE; `Cliente.usuario` devuelve objeto | 5, 10 | ✅ | ✅ | `uselist=False` y test de objeto | 04; C-06 |
| C08 | `libro.borrado_en` timestamptz nulo; índice único parcial (isbn) WHERE borrado_en IS NULL **en lugar del** UNIQUE; siguen CHECK precio > 0 y stock >= 0 | 5 | ✅ | ⚠️ | Nombre real `uq_libro_isbn` (C-06 decía `libro_isbn_key`) | 04, 11; C-06 |
| C09 | `movimiento_stock(id, libro_id, venta_id nulo, usuario_id, cantidad, motivo, cuando)`; CHECK cantidad <> 0; sólo agregado | 6 | ⚠️ | ⚠️ | `usuario_id` NOT NULL (sin "(nulo)" + Fig. 1 multiplicidad 1); Q-08 resuelta en esa parte | 04, 10 Q-08; C-06 |
| C10 | Todas las fechas nuevas `timestamptz` | 6 | ✅ | ❌ | Lista de columnas timestamptz en 04 y C-06 | 04; C-06 |
| C11 | Dinero `NUMERIC` / `Decimal`, nunca float | 6 | ✅ | ❌ | Agregado a C-06 | C-06 |
| C12 | Índice en **cada** FK nueva | 6 | ⚠️ | ⚠️ | Lista concreta (incluye `asignacion_rol.usuario_id`, que el índice parcial no cubre) | 04; C-06 |
| C13 | Navegación declarada en los dos extremos | 6 | ⚠️ | ⚠️ | Pares `back_populates` enumerados + tests | 04; C-06 |
| C14 | Composición Venta◆RenglonVenta 1..*; agregación Libro–Editorial (1) y Libro–Genero (0..1); asociaciones; IntentoAcceso/EventoSeguridad sin relaciones | 5 (Fig. 1) | ⚠️ | — | ERD reescrito desde la imagen de la Fig. 1 | 04 §ERD |
| C15 | Nulabilidad: nulo sólo donde dice "(nulo)" | 5-6 | ❌ | ❌ | Agregado | 04; C-06 |
| C16 | Módulo de cada entidad (AsignacionRol/IntentoAcceso/EventoSeguridad en usuarios; MovimientoStock y LibroAutor en libros; PerfilCliente en clientes; RenglonVenta en ventas) | 9 | ✅ | ⚠️ | Archivos destino explícitos en C-06 | 04, 08; C-06 |
| C17 | Invariante `stock == SUM(movimientos)` verificada tras cada caso de venta | 6 | ✅ | ✅ | — | 04; C-12, C-14, C-16 |
| C18 | Roles: sin columna `rol` en usuario; revocar escribe `revocada_en`; nunca se borra | 6 | ✅ | ✅ | — | 03, 04; C-11 |
| C19 | Esquema sólo con Alembic, sin `create_all` | 10, 20 | ✅ | ⚠️ | conftest de C-02 con "nunca create_all" | C-02 |
| C20 | 0003 autogenerada, leída, con comentario; corregida a mano con comentario si hace falta | 10 | ✅ | ✅ | Riesgo de drops espurios por UNIQUE sin nombre en los modelos | 11; C-06 |
| C21 | 0004 a mano con el disparador (autogenerate no ve funciones/disparadores) | 10 | ✅ | ✅ | — | C-07 |
| C22 | `upgrade head` (vacía) → `downgrade base` → `upgrade head` | 10 | ✅ | ⚠️ | Ciclo completo explícito en C-07 | C-07 |

### D. Reglas de negocio (p. 6-8)
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| D01 | RN-01 unicidades; ISBN entre vigentes — UNIQUE e índice único parcial; 409 con mensaje propio | 7 | ✅ | ✅ | — | 05 |
| D02 | RN-02 registro usuario+CLIENTE+cliente, todo o nada; 409 si existe cliente con ese correo, sin apropiarse — un solo UoW | 7 | ✅ | ⚠️ | C-09: un bloque, 409 por UNIQUE sin consulta previa | C-09 |
| D03 | RN-03 una asignación abierta por rol — índice único parcial; 409 | 7 | ✅ | ❌ | Agregado a C-11 | C-11 |
| D04 | RN-04 permisos con roles vigentes en la base por petición; token informativo — dependencia que consulta `asignacion_rol` | 7 | ✅ | ✅ | — | C-10 |
| D05 | RN-05 no revocarse el propio ADMIN **y nunca quedar sin administradores** — comprobación en el servicio; 409 | 7 | ✅ | ❌ | "Nunca cero admins" agregado a C-11 | C-11 |
| D06 | RN-06 con cambio pendiente sólo `/auth` y rutas sin sesión — dos grupos; 403 | 7 | ✅ | ⚠️ | `/auth/yo` y `cambiar-password` en el grupo abierto | 03, 06; C-10 |
| D07 | RN-07 5 fallos (email, ip) en 60 s → 429 sin verificar; login correcto reinicia — conteo sobre `intento_acceso`; Retry-After | 7 | ✅ | ⚠️ | "Login correcto reinicia la cuenta" en C-09; anotar o no el 429 **(Q-20)** | C-09; 10 Q-20 |
| D08 | RN-08 misma respuesta y tiempo exista o no el correo — hash ficticio | 7 | ✅ | ✅ | — | C-09 |
| D09 | RN-09 venta con ≥1 renglón sin libros repetidos, precio copiado, total del servidor, sin PATCH — DTO | 7 | ✅ | ⚠️ | Contrato 422 y "no hay PATCH" en C-14 | C-14 |
| D10 | RN-10 venta + descuento + movimiento por renglón; si no alcanza, nada — un solo UoW; 409 | 7 | ✅ | ✅ | — | C-14 |
| D11 | RN-11 stock sólo por movimientos (alta, reposición, venta), no PATCH — punto único | 7 | ✅ | ✅ | — | C-12 |
| D12 | RN-12 `movimiento_stock` sólo agregado — disparador por migración | 7 | ✅ | ✅ | Gotcha TRUNCATE para seed/tests (DD-10) | 04, 09; C-02, C-07, C-16 |
| D13 | RN-13 dado de baja: fuera del catálogo, no se vende **ni repone**, ventas viejas lo muestran — borrado lógico; 409 | 7 | ⚠️ | ⚠️ | Reponer dado de baja 409, listados por editorial/género/autor sin dados de baja; `GET /libros/{id}` de dado de baja **(Q-19)** | 05 §Baja lógica; C-12; 10 Q-19 |
| D14 | RN-14 lo propio sólo pide autenticación — `/mis-ventas` y dueño; 403 | 8 | ✅ | ✅ | `GET /ventas/{id}` sin `requiere_rol` explícito en C-14 | C-14 |
| D15 | RN-15 nunca texto de la base; ninguna entrada inválida en 500 — traducción del `IntegrityError`; validación en el contrato | 8 | ⚠️ | ⚠️ | Sección "Manejo de errores" completa (incluye overflow `int4`) | 05; C-04, C-15 |
| D16 | RN-16 alta de personal, **cambio de rol y cambio de contraseña** → `evento_seguridad` en la misma transacción — un solo UoW | 8 | ✅ | ❌ | C-11 sólo cubría cambio de rol: se agregaron alta de personal (C-11) y cambio de contraseña (C-09) | 07 Flujo 3b; C-09, C-11 |
| D17 | Siguen vigentes CHECK de precio/stock y búsqueda por título con parámetros ligados | 6 | ✅ | ⚠️ | Búsqueda ILIKE ligada en C-12 | C-12, C-15 |

### E. Estructura obligatoria (p. 8-9)
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| E01 | `seed.py` deja la base en el estado inicial conocido | 8 | ✅ | ⚠️ | Ubicación raíz y TRUNCATE | C-16 |
| E02 | `app/core/config.py`, `database.py` | 8 | ✅ | ✅ | — | C-03 |
| E03 | `app/core/security.py`: bcrypt fuera del bucle, emisión/verificación del token | 8 | ✅ | ✅ | — | C-08 |
| E04 | `app/core/dependencies.py`: usuario actual, roles vigentes, control del cambio obligatorio, `requiere_rol` | 8 | ✅ | ⚠️ | Las cuatro piezas explícitas | C-10 |
| E05 | `app/core/repository.py`: `BaseRepository[T]` y `SoftDeleteRepository[T]` | 8 | ✅ | ❌ | C-04 decía `Repository[T]` | C-04 |
| E06 | `app/core/paginacion.py`; `app/core/unit_of_work.py` (confirma o revierte al salir) | 8 | ✅ | ✅ | — | C-04 |
| E07 | Por módulo: `models`, `schemas`, `repository`, `unit_of_work`, `service`, `router` | 8-9 | ✅ | ⚠️ | Archivos explícitos en C-05, C-09, C-12, C-13, C-14 | CHANGES |
| E08 | `service.py` recibe el UoW y lo abre; `router.py` construye el UoW, llama al servicio y **traduce errores** | 9 | ⚠️ | ⚠️ | KB decía "router/servicio" traducen; corregido a router | 08, 05, 11; C-04, C-05 |
| E09 | `migrations/`; `test/` con `.http` y `solo_agregado.sql` | 9 | ✅ | ✅ | — | C-07, C-17 |
| E10 | Módulos mínimos (8); `health` sólo `router.py` | 9 | ✅ | ✅ | Borrar `health/service.py` explícito | C-03 |
| E11 | El despliegue no forma parte de esta estructura (carpeta aparte) | 9 | ✅ | ✅ | — | 09 DD-03 |

### F. Consignas (Ej. 3-8, p. 10-13)
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| F01 | Contratos separados de los modelos de tabla | 10 | ✅ | ⚠️ | Explícito en C-05 | C-05 |
| F02 | `extra="forbid"` (nadie se registra con rol ni edita stock) | 10 | ✅ | ✅ | — | C-05, C-09, C-12 |
| F03 | Ninguna respuesta con `password_hash` | 10 | ✅ | ✅ | — | C-09, C-15 |
| F04 | PATCH con `exclude_unset` | 10 | ✅ | ✅ | — | C-05 |
| F05 | Códigos 201/204/404/409/422 | 10 | ✅ | ⚠️ | Códigos por endpoint en cada change | C-05, C-09, C-11..C-14 |
| F06 | Envoltorio `{items,total,page,size,pages}`; page ≥ 1; size 1..100 default 20; página de más 422; total con mismos filtros; 0 resultados = una página vacía | 10 | ✅ | ✅ | Default 20 y mensaje en C-04 | C-04 |
| F07 | Búsqueda por título ligada y sin distinguir mayúsculas | 10 | ✅ | ⚠️ | C-12 | C-12 |
| F08 | bcrypt con costo en config; `to_thread` + semáforo | 11 | ✅ | ✅ | — | C-08 |
| F09 | Hash antes de abrir la transacción | 11 | ✅ | ❌ | En registro, alta de personal y cambio de contraseña | C-09, C-11 |
| F10 | Todo campo que termina en bcrypt ≤ 72 **bytes** (incluye login y actual) → 422 | 11 | ✅ | ⚠️ | En el contrato (C-09), no sólo en `security.py` | C-08, C-09 |
| F11 | Orden del login: límite (1 consulta, 429 + Retry-After sin hash) → verificación (hash real o ficticio) | 11 | ✅ | ✅ | — | C-09 |
| F12 | JWT con `sub`, `exp` y roles vigentes | 11 | ✅ | ⚠️ | Claims explícitos | C-08 |
| F13 | Cookie `access_token` HttpOnly, SameSite=Lax, Max-Age = duración, Secure configurable; cuerpo sin token; lectura de `request.cookies` | 11 | ✅ | ⚠️ | Nombre de la cookie | C-08, C-10 |
| F14 | Cambiar contraseña no invalida sesiones ni emite token | 11 | ✅ | ❌ | Agregado a C-09 | C-09 |
| F15 | Registro, cierre de sesión que borra la cookie, `GET /auth/yo` (usuario, roles vigentes y del token) | 11 | ✅ | ❌ | Logout era GET en CHANGES; `/auth/yo` sin detalle | 06; C-09 |
| F16 | `get_usuario_actual` 401: sin cookie, token inválido/vencido, usuario inexistente **o inactivo** | 11 | ✅ | ⚠️ | "inactivo" agregado | C-10 |
| F17 | `requiere_rol` 403; revocar quita permiso a la sesión abierta | 11 | ✅ | ✅ | — | C-10, C-11 |
| F18 | Asignar con vencimiento opcional; revocar sin borrar; **reasignar un vencido cierra la fila anterior y abre una nueva** | 11 | ✅ | ❌ | Agregado a C-11 | C-11 |
| F19 | Vencimiento con zona y futuro; si no 422 (no 409) | 11 | ✅ | ✅ | — | C-11 |
| F20 | Dos grupos de rutas en `main.py`, control montado una vez | 11 | ✅ | ✅ | — | C-10 |
| F21 | Actor `SISTEMA` (texto) para los datos iniciales | 11 | ✅ | ✅ | — | C-11, C-16 |
| F22 | `BaseRepository` recibe sesión y clase del modelo; métodos mínimos | 12 | ✅ | ❌ | C-04 | C-04 |
| F23 | `SoftDeleteRepository` hereda, lo usa Libro, filtra, agrega `get_by_id_including_deleted` y `soft_delete` | 12 | ✅ | ⚠️ | C-04 | C-04, C-12 |
| F24 | `add`/`update` hacen `flush()`, ningún repositorio confirma | 12 | ✅ | ✅ | — | C-04 |
| F25 | Repositorio por entidad, métodos nombrados por lo que traen; precarga dentro del método | 12 | ✅ | ⚠️ | Repos por entidad listados por módulo | C-09, C-12..C-15 |
| F26 | UoW base: confirma al salir, revierte con excepción, **no cierra la sesión** | 12 | ✅ | ⚠️ | Test "la sesión sigue abierta" | C-04 |
| F27 | UoW por módulo con los repositorios necesarios, misma sesión | 12 | ✅ | ⚠️ | C-04 patrón; C-14 compone ventas+clientes+libros | C-04, C-14 |
| F28 | Router construye el UoW con dependencia y no lo abre; servicio lo abre con `async with` y nunca lo construye | 12 | ✅ | ⚠️ | Premisa 8 + C-04 + auditoría `grep` en C-15 | CHANGES |
| F29 | RN-02, RN-10, RN-16 cada una en un solo bloque | 12 | ✅ | ⚠️ | Explícito en C-09, C-11, C-14 | CHANGES |
| F30 | Dependencias de usuario y rol con la **misma sesión** que el UoW | 12 | ✅ | ❌ | Agregado a C-10 | 03, 07; C-10 |
| F31 | Stock en un único punto usado por alta, reposición y ventas | 12 | ✅ | ✅ | — | C-12, C-14 |
| F32 | Disparador rechaza UPDATE/DELETE venga de donde venga | 12 | ✅ | ✅ | — | C-07 |
| F33 | `intento_acceso` (correcto o fallido) en sesión y transacción propias, siempre confirmadas; comentario con qué/por qué/costo | 12 | ✅ | ⚠️ | Comentario de tres puntos + UoW propio (DD-09) | 07, 08, 09; C-09 |
| F34 | Respuestas con relaciones vía carga anticipada en el repositorio; detalle de venta con consultas fijas, incluye libro dado de baja; sin carga perezosa | 13 | ✅ | ✅ | — | C-15 |
| F35 | Handlers `async def`, sin llamadas bloqueantes | 13 | ✅ | ✅ | — | C-15 |
| F36 | Aviso con `BackgroundTasks` (`sleep(0.5)` + log), después de la respuesta, sólo si confirmó, visible con uvicorn por defecto | 13 | ✅ | ⚠️ | `sleep(0.5)` explícito | C-14 |

### G. Endpoints de referencia (p. 16-18) — verificados fila por fila
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| G01 | Health (2 filas) | 16 | ✅ | ✅ | — | 06; C-03 |
| G02 | Auth (5 filas): `POST /auth/logout`, `/auth/yo` y `cambiar-password` en grupo abierto | 16 | ✅ | ❌ | CHANGES decía `GET /auth/logout`; Q-11 resuelta; contraseña actual errónea **(Q-11 residual)** | 06, 10; C-09 |
| G03 | Catálogo público (`/libros`, `/libros/{id}`, `/editoriales`, `/generos`, `/{x}/{id}/libros`) | 16-17 | ✅ | ⚠️ | Códigos en C-05/C-12; paginación de `/{x}/{id}/libros` **(Q-18)** | 06; C-05, C-12 |
| G04 | Usuarios/roles/eventos ADMIN (5 filas) | 17 | ✅ | ❌ | `GET /usuarios/{id}/roles` y `GET /eventos` no estaban en ningún change | C-11 |
| G05 | Catálogo ADMIN (POST/PATCH editoriales, géneros, autores) | 17 | ✅ | ⚠️ | Códigos en C-05 | C-05 |
| G06 | Libros ADMIN (POST, PATCH, DELETE, reponer, movimientos) | 17 | ✅ | ❌ | `GET /libros/{id}/movimientos` faltaba | C-12 |
| G07 | Clientes VENDEDOR/ADMIN (4 filas) | 17 | ✅ | ⚠️ | Códigos en C-13 | C-13 |
| G08 | Ventas: POST y GET (VENDEDOR, ADMIN), `/ventas/{id}` (personal o dueño, 200/403/404), `/mis-ventas` (autenticado) | 18 | ✅ | ⚠️ | Q-12 resuelta; `GET /ventas` en C-14 | 10; C-14 |
| G09 | Todo el grupo protegido: 401 sin sesión, 403 con cambio pendiente | 18 | ✅ | ✅ | — | C-10 |
| G10 | Detalle de venta sin `requiere_rol`; el servicio decide | 18 | ✅ | ⚠️ | Explícito en C-14 | C-14 |
| G11 | Rutas del TP no listadas (GET /autores, GET por id, PATCH /generos, GET /clientes) | — | ⚠️ | ⚠️ | Lista completa **(Q-10)** | 03, 06, 10, 11 |

### H. Ejemplos y datos iniciales (p. 18-20)
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| H01 | Cuerpo de `POST /ventas` (sin precio, total ni fecha) | 18 | ✅ | ✅ | — | 06 |
| H02 | Cuerpo de `POST /libros` con `stock_inicial` y `autores`; deja "Stock inicial" | 18-19 | ✅ | ✅ | — | 06; C-12 |
| H03 | Login: `{mensaje, debe_cambiar_password, expira_en_segundos}`; token en `Set-Cookie` | 19 | ✅ | ❌ | Agregado a C-09 | C-09 |
| H04 | Ejemplo de listado (`total 5, pages 3`; page=4 → 422 "La página 4 no existe: hay 3") | 19 | ✅ | ⚠️ | Mensaje en C-04; orden de ids del seed | 10 IN-03; C-04 |
| H05 | `seed.py` vacía las tablas y carga el mínimo; contraseñas de mentira sólo ahí | 19 | ✅ | ⚠️ | TRUNCATE (DD-10) | C-16 |
| H06 | Usuarios del seed (5) con roles y `nuevo` con cambio obligatorio | 19 | ✅ | ⚠️ | Explícitos en C-16 | C-16 |
| H07 | 3 editoriales, 3 géneros, 6 autores; 5 libros con stock; clientes Lucía (perfil), Tomás, Ana (usuario) | 20 | ✅ | ✅ | Orden de ids sugerido por el PDF | 10 IN-02/IN-03; C-16 |
| H08 | Venta 1 de Lucía por vendedor (1 Rayuela + 2 Ficciones = 69000.00); movimientos Stock inicial (11 y 10) y salidas −1/−2 | 20 | ✅ | ⚠️ | Explícito en C-16; usuario de "Stock inicial" **(Q-08)** | C-16 |
| H09 | Línea `SISTEMA` "Carga de los datos iniciales" | 20 | ✅ | ✅ | — | C-16 |

### I. Requisitos no funcionales (p. 20-21)
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| I01 | Asincronía; bcrypt siempre fuera del bucle | 20 | ✅ | ✅ | — | 02 |
| I02 | Credenciales: ninguna en código, default, `alembic.ini`, repo ni imagen | 20 | ✅ | ✅ | — | 02; C-03, C-22 |
| I03 | Token sólo en cookie; nunca cuerpo ni `Authorization` | 20 | ✅ | ✅ | — | C-10 |
| I04 | Esquema sólo con Alembic | 20 | ✅ | ⚠️ | C-02 | C-02 |
| I05 | Ningún repositorio confirma; ningún servicio construye su UoW; el UoW no cierra la sesión | 20 | ✅ | ⚠️ | Premisa 8 | CHANGES |
| I06 | Carga perezosa prohibida | 20 | ✅ | ✅ | — | C-15 |
| I07 | SQL nunca por concatenación | 20 | ✅ | ✅ | — | C-15 |
| I08 | Errores: mensajes propios, nunca texto de la base ni traza, ninguna entrada inválida en 500 | 20 | ⚠️ | ⚠️ | 05 §Manejo de errores | 05; C-04, C-15 |
| I09 | Unicidad garantizada por la base, **sin consulta previa** | 20 | ✅ | ❌ | Agregado a C-04 y C-09 | 05; C-04, C-09 |
| I10 | Contenedor: alpine, no root, sin secretos | 20 | ✅ | ✅ | — | C-20 |
| I11 | Diagnóstico con `SQL_ECHO=true` | 21 | ✅ | ✅ | — | C-03 |

### J. Casos de prueba (p. 21-23)
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| J01 | `.http` en `test/` con respuesta esperada en comentario; `python seed.py` antes de cada archivo | 21 | ✅ | ✅ | — | C-17 |
| J02 | C-01..C-16 | 21-22 | ✅ | ⚠️ | C-01 sin test asignado: agregado a C-10 | C-10, C-17 |
| J03 | `test/solo_agregado.sql` (C-14) y captura de psql | 21, 24 | ✅ | ✅ | — | C-07, C-17 |
| J04 | Varias sesiones con REST Client (`# @name`, `# @no-cookie-jar`, `Cookie:`) | 23 | ✅ | ✅ | — | C-17 |
| J05 | D-01..D-08 sobre el TP desplegado, salida en `despliegue/evidencia/` | 22-23 | ✅ | ⚠️ | D-01 aclarado (límite de la imagen base) | 12; C-20, C-21 |

### K. Contenedor, despliegue, criterios y entrega (p. 14-16, 23-24)
| # | Requisito | Pág. | KB antes | CHANGES antes | Corrección aplicada | Dónde |
|---|---|---|---|---|---|---|
| K01 | TP Cap 1-4 tal como se entregó; sólo se agregan Dockerfile y `.dockerignore`; defectos propios se corrigen y se anotan en DEPLOY.md | 14 | ✅ | ✅ | — | C-19, C-20 |
| K02 | `FROM python:3.12-alpine` (límite de 100 MB de la base) | 14 | ✅ | ⚠️ | C-20 decía "tamaño < 100 MB" sin aclarar que es la base | 12; C-20 |
| K03 | requirements antes del código con `--no-cache-dir`; usuario sin privilegios + `USER`; `.dockerignore` (`.env`, `.venv`, `.git`, `__pycache__`); sin secretos | 14 | ✅ | ✅ | — | C-20 |
| K04 | Al arrancar `alembic upgrade head` y luego uvicorn `0.0.0.0`; si Alembic falla, el contenedor termina con error | 14 | ⚠️ | ⚠️ | Encadenado `&&` explícito | 12; C-20 |
| K05 | HEALTHCHECK sobre `/health/ready` con `127.0.0.1` (wget, no curl) | 14-15 | ✅ | ✅ | — | C-20 |
| K06 | `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file ...`; `DATABASE_URL` asyncpg + `SQL_ECHO=false`; no localhost; `--add-host` | 15 | ✅ | ✅ | — | 07 Flujo 7; C-21 |
| K07 | Despliegue en el VPS, en línea hasta las notas; seed vía `docker exec` | 16 | ✅ | ✅ | Bloqueado por Q-02 | C-21 |
| K08 | DEPLOY.md completo (URL, fecha/hora, comandos, cambios, actualización) | 16 | ✅ | ✅ | — | C-21 |
| K09 | Puntos/pesos por ejercicio (100) y reglas duras | 23-24 | ✅ | ✅ | — | 12 |
| K10 | Zip `Parcial_Cap1a6_<Grupo>.zip` con `parcial/` (código, requirements, env.example, alembic.ini, migrations, test, README, evidencia C-14/C-15) y `despliegue/` (TP + Dockerfile, .dockerignore, env.example, DEPLOY.md, evidencia D) | 24 | ✅ | ✅ | — | 12; C-22 |
| K11 | README de `parcial/` con integrantes y pasos desde cero (incluye cómo generar la clave de firma) | 24 | ✅ | ✅ | — | C-18 |
| K12 | Sin `.venv`, `__pycache__`, `.env`; si va `.git`, se revisa el historial | 24 | ✅ | ✅ | — | C-22 |

## Conteo
| | ✅ antes | ⚠️ antes | ❌ antes | — (no aplica) |
|---|---|---|---|---|
| KB (153 requisitos) | 137 | 15 | 1 | 0 |
| CHANGES.md (153 requisitos) | 67 | 64 | 19 | 3 |

Después de las correcciones: KB 153/153 ✅ y CHANGES.md 150/150 aplicables ✅; quedan **8 decisiones abiertas** que el PDF no resuelve y que no bloquean la planificación: Q-03 (confirmar `main.py` en la raíz), Q-08 (usuario de los "Stock inicial"), Q-10 (rutas del TP no listadas), Q-11 residual (código de contraseña actual errónea), Q-17 (`otorgada_por` FK), Q-18 (paginación de `/{x}/{id}/libros` y `/movimientos`), Q-19 (operaciones sobre libro dado de baja), Q-20 (si el 429 se anota). Siguen además las preguntas de la cátedra/grupo ya existentes (Q-01, Q-02, Q-05, Q-06, Q-13, Q-14, Q-15).

## Archivos modificados por la auditoría
`knowledge-base/03_actores_y_roles.md`, `04_modelo_de_datos.md`, `05_reglas_de_negocio.md`, `06_funcionalidades.md`, `07_flujos_principales.md`, `08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`, `11_brecha_tp_vs_parcial.md`, `12_entregables_del_parcial.md`, `README.md`, este archivo, y `CHANGES.md` (changelog, premisas 6 y 8, C-02..C-09, C-10..C-16, C-20, punteros de "Leer antes").
