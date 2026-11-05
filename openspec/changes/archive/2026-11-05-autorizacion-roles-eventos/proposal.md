# Proposal

## Why

El Ej. 5 del PDF (12 puntos) pide autorización por roles vigentes **en la base, en cada petición** (RN-04), distinguir 401 de 403, gestión de roles con vencimiento y revocación sin borrar (RN-03), autoprotección del administrador (RN-05), el cambio obligatorio de contraseña resuelto con **dos grupos de rutas en `main.py`** (RN-06) y el historial de seguridad con el actor `SISTEMA`; el Ej. 7 suma que cada alta de personal y cambio de rol deje su evento **en la misma transacción** (RN-16). Hoy (tras C-05) cualquier visitante puede crear editoriales, libros, clientes y ventas: sólo existe la autenticación. Es requisito de C-07 (libros, clientes y ventas con sus roles).

## What Changes

- **`app/core/dependencies.py`** (se completa lo de C-05, sin duplicarlo): `get_usuario_actual` pasa a cargar también los **roles vigentes** de `asignacion_rol` en el mismo bloque de lectura y con la misma sesión que el UoW; nuevo control del **cambio obligatorio** (403); nueva fábrica `requiere_rol(*roles)` (403). `Authorization: Bearer` sigue ignorado (401).
- **`main.py`**: dos grupos de rutas — **abierto** (health, `/auth/*`, catálogo público) y **protegido** (un `APIRouter` con el control del cambio obligatorio montado **una sola vez**). Cada router de módulo se separa en su parte pública y su parte protegida según la matriz de `knowledge-base/03`.
- **Protección de las rutas existentes** según la matriz: escrituras de editoriales/géneros/autores/libros → ADMIN; clientes y ventas → VENDEDOR, ADMIN (las rutas del TP de libros/clientes/ventas siguen con su lógica actual hasta C-07; aquí sólo se les monta la autorización).
- **Nuevos endpoints** (grupo protegido, ADMIN), en el módulo `usuarios`:
  - `POST /usuarios` → 201/409/422: alta de personal con contraseña provisoria hasheada **antes** del UoW; usuario con `debe_cambiar_password=true` + rol + evento en **un bloque**.
  - `GET /usuarios/{id}/roles` → 200/404: historial de asignaciones con su vigencia.
  - `POST /usuarios/{id}/roles` → 201/404/409/422: `vence_en` opcional, **con zona y futuro** (si no, 422); segunda asignación abierta vigente → 409 por el índice único parcial (RN-03); un rol vencido se reasigna cerrando la fila anterior y abriendo otra; evento en el mismo bloque.
  - `DELETE /usuarios/{id}/roles/{rol}` → 200/404/409: escribe `revocada_en`, nunca borra; revocarse el ADMIN propio o dejar el sistema sin administradores vigentes → 409 (RN-05); evento en el mismo bloque.
  - `GET /eventos` (`page`, `size`) → 200/422: historial de seguridad paginado.
- **Actor `SISTEMA`**: constante textual para los eventos de los datos iniciales (la usa `seed.py` en C-09).
- **Errores**: los 403 de autorización los lanzan las dependencias (capa HTTP); RN-05 usa el `Conflicto` (409) existente. No se agregan tipos de error (el 403 decidido por un servicio, para "lo propio", llega con C-07).
- Archivo `.http` con los casos C-01, C-06 (401/403), C-07, C-08 y C-09 del PDF.

Fuera de alcance: `GET /mis-ventas`, la comprobación de dueño de `GET /ventas/{id}` y la lógica nueva de libros/clientes/ventas (C-07); `seed.py` y las contraseñas del seed (C-09, Q-05); revocación de tokens (la consigna no la pide: los roles se releen de la base).

## Capabilities

### New Capabilities
- `autorizacion`: 401 contra 403, roles vigentes leídos de la base en cada petición, `requiere_rol`, control del cambio obligatorio y los dos grupos de rutas con la matriz de permisos.
- `gestion-roles`: alta de personal, consulta, asignación con vencimiento y revocación de roles con RN-03 y RN-05.
- `eventos-seguridad`: eventos de RN-16 en la misma transacción que el cambio, actor `SISTEMA` y `GET /eventos`.

### Modified Capabilities
- `catalogo-referencias`: el alta (`POST`) y la modificación (`PATCH`) de editoriales, géneros y autores pasan a exigir sesión y rol ADMIN (401/403); las consultas siguen públicas.

## Impact

- Código: `parcial/app/core/dependencies.py`, `parcial/app/modules/usuarios/{schemas,repository,unit_of_work,service,router}.py`, los `router.py` de `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas` (sólo el reparto en público/protegido y `requiere_rol`), `parcial/main.py`, `parcial/test/` (un `.http` nuevo).
- API: cinco rutas nuevas; las escrituras del catálogo y todas las rutas de clientes y ventas pasan a responder 401/403 sin la sesión o el rol adecuados (**BREAKING** respecto del TP, exigido por el PDF).
- Sin cambios de esquema ni migraciones (las tablas existen desde C-03); sin dependencias nuevas.
- Governance CRÍTICO (autorización/seguridad): el apply requiere aprobación explícita del usuario y la resolución de las preguntas abiertas del `design.md`.
