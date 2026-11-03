# Actores y Roles

## Actores del sistema
| Actor | Descripción | Cómo interactúa |
|---|---|---|
| Anónimo | Cualquier visitante | Catálogo público (`GET /libros`, listados de editoriales/géneros), `/auth/registro`, `/auth/login`, health |
| CLIENTE | Persona que se auto-registra | `/auth/*`, `/mis-ventas`, `GET /ventas/{id}` de su propia venta |
| VENDEDOR | Personal de mostrador | Clientes y ventas |
| ADMIN | Administrador | Catálogo, reposición, usuarios/roles, eventos; además lo de VENDEDOR |
| SISTEMA | Actor **textual**, no un usuario | Aparece en `evento_seguridad.actor` para la carga de datos iniciales |

Los roles viven en `asignacion_rol` (no hay columna `rol` en `usuario`). Rol vigente = fila no revocada (`revocada_en IS NULL`) y sin vencer (`vence_en` nulo o futuro). Valores válidos (CHECK): `ADMIN`, `VENDEDOR`, `CLIENTE`. Revocar escribe `revocada_en`; la fila nunca se borra (historial).

## RBAC — matriz (derivada de la tabla "Endpoints de referencia")
| Ruta | Anónimo | CLIENTE | VENDEDOR | ADMIN |
|---|---|---|---|---|
| `GET /health/live`, `/health/ready`, `POST /auth/registro`, `/auth/login`, `/auth/logout` | sí | sí | sí | sí |
| `GET /auth/yo`, `POST /auth/cambiar-password` | 401 | sí | sí | sí |
| `GET /libros`, `/libros/{id}`, `GET /editoriales`, `/generos` | sí | sí | sí | sí |
| `GET /editoriales/{id}/libros`, `/generos/{id}/libros`, `/autores/{id}/libros` | sí | sí | sí | sí |
| `GET /mis-ventas` | 401 | sí | sí | sí (Autenticado) |
| `GET /ventas/{id}` | 401 | sólo si es dueño, si no 403 | sí | sí |
| `POST /clientes`, `GET/PATCH /clientes/{id}`, `POST /clientes/{id}/perfil`, `GET /clientes/{id}/ventas` | 401 | 403 | sí | sí |
| `POST /ventas`, `GET /ventas` | 401 | 403 | sí | sí |
| `POST /editoriales,/generos,/autores`, `PATCH /editoriales/{id},/autores/{id}` | 401 | 403 | 403 | sí |
| `POST /libros`, `PATCH/DELETE /libros/{id}`, `POST /libros/{id}/reponer`, `GET /libros/{id}/movimientos` | 401 | 403 | 403 | sí |
| `POST /usuarios`, `GET/POST /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}`, `GET /eventos` | 401 | 403 | 403 | sí |

Matriz verificada contra la tabla p. 16-18 (`13_auditoria_vs_pdf.md`). El PDF no lista `PATCH /generos/{id}` (aunque sí `PATCH /editoriales/{id}, /autores/{id}`), ni `GET /autores`, `GET /{editoriales,generos,autores}/{id}` ni `GET /clientes` (ver `10_preguntas_abiertas.md`, Q-10). `GET /auth/yo` y `POST /auth/cambiar-password` piden sesión pero están en el grupo **abierto** (sin el control del cambio obligatorio). Las dependencias de autenticación usan la misma sesión que el UoW de la petición (una sola conexión del pool).

`GET /ventas/{id}` **no lleva `requiere_rol`**: un cliente dueño no tiene rol de personal. La decisión la toma el servicio: primero quién es y qué relación tiene con la venta (403 si no es ni personal ni dueño) y recién después qué se devuelve.

## Reglas transversales de acceso
- **401**: sin cookie, token inválido o vencido, usuario inexistente o inactivo (`get_usuario_actual`).
- **403**: autenticado sin rol vigente suficiente (`requiere_rol`, consulta la base en cada petición; los roles del token son sólo informativos, RN-04) o con cambio de contraseña pendiente (RN-06).
- Toda ruta del grupo protegido responde además 401 sin sesión y 403 con cambio pendiente.
- Un ADMIN no puede revocarse su propio ADMIN y nunca puede quedar el sistema sin administradores vigentes (RN-05).
- Revocar un rol quita el permiso a una sesión ya abierta, sin esperar el vencimiento del token.
- RN-06: con cambio pendiente sólo se pueden usar rutas de `/auth` y las que no piden sesión.

## Rutas públicas (sin sesión)
`GET /health/live`, `GET /health/ready`, `POST /auth/registro`, `POST /auth/login`, `POST /auth/logout`, `GET /libros`, `GET /libros/{id}`, `GET /editoriales`, `GET /generos`, `GET /editoriales/{id}/libros`, `GET /generos/{id}/libros`, `GET /autores/{id}/libros`.

## Usuarios de los datos iniciales (seed.py)
| Email | Rol(es) | Notas |
|---|---|---|
| admin@example.com | ADMIN | |
| admin2@example.com | ADMIN | segundo admin (permite probar autoprotección sin quedar sin admins) |
| vendedor@example.com | VENDEDOR | registró la venta 1 |
| ana@example.com | CLIENTE | cliente "Ana Paz", con usuario |
| nuevo@example.com | VENDEDOR | con `debe_cambiar_password = true` (caso C-09) |

Las contraseñas del seed son de mentira y viven sólo en `seed.py` (los valores concretos no los fija el PDF: ver Q-05).
