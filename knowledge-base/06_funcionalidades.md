# Funcionalidades

Organizadas por épica. Los códigos son los de la tabla "Endpoints de referencia" del PDF (p. 16-18), **verificada** fila por fila (grupo, método, ruta, quién, códigos) con `pdftotext -table` en la auditoría `13_auditoria_vs_pdf.md`. Las rutas del PDF van **sin barra final**; el TP actual declara `"/"` (ver `11_brecha_tp_vs_parcial.md`).

**Grupo** (columna del PDF): *Abierto* = no pide sesión ni lleva el control del cambio obligatorio; *Protegido* = lleva el control del cambio obligatorio montado una sola vez. Ojo: `GET /auth/yo` y `POST /auth/cambiar-password` están en el grupo **Abierto** aunque piden estar autenticado (por eso el usuario con cambio pendiente puede cambiar la contraseña).

**Rutas que el PDF no lista** (el TP las tiene): `GET /autores` (listado), `GET /editoriales/{id}`, `GET /generos/{id}`, `GET /autores/{id}`, `PATCH /generos/{id}`, `GET /clientes` (listado). Ver Q-10.

## Épica 1 — Salud (Ej. 1) — módulo `health` (sólo `router.py`)
| Método | Ruta | Quién | Códigos |
|---|---|---|---|
| GET | `/health/live` | Cualquiera | 200 (no toca la base) |
| GET | `/health/ready` | Cualquiera | 200, 503 (ejecuta `SELECT 1`; 503 si la base no contesta) |

## Épica 2 — Auth (Ej. 4) — grupo abierto
| Método | Ruta | Quién | Códigos |
|---|---|---|---|
| POST | `/auth/registro` | Cualquiera | 201, 409, 422 |
| POST | `/auth/login` | Cualquiera | 200, 401, 422, 429 |
| POST | `/auth/logout` | Cualquiera | 200 (borra la cookie; **POST**, no GET) |
| GET | `/auth/yo` | Autenticado | 200, 401 (usuario, roles vigentes y roles del token) |
| POST | `/auth/cambiar-password` | Autenticado | 200, 401, 422 (pone `debe_cambiar_password=false`, deja evento RN-16, no emite token nuevo) |

## Épica 3 — Catálogo público y referencias
| Método | Ruta | Quién | Códigos |
|---|---|---|---|
| GET | `/libros` (`page`, `size`, `titulo`, `genero_id`) | Cualquiera | 200, 422 |
| GET | `/libros/{id}` | Cualquiera | 200, 404, 422 |
| GET | `/editoriales`, `/generos` (`page`, `size`) | Cualquiera | 200, 422 |
| GET | `/editoriales/{id}/libros`, `/generos/{id}/libros`, `/autores/{id}/libros` | Cualquiera | 200, 404 |
| POST | `/editoriales`, `/generos`, `/autores` | ADMIN | 201, 409, 422 |
| PATCH | `/editoriales/{id}`, `/autores/{id}` | ADMIN | 200, 404, 409, 422 |

## Épica 4 — Libros y stock (ADMIN)
| Método | Ruta | Códigos |
|---|---|---|
| POST | `/libros` (con `autores` y `stock_inicial`; deja movimiento "Stock inicial") | 201, 409, 422 |
| PATCH | `/libros/{id}` (título y precio; **el stock no**) | 200, 404, 409, 422 |
| DELETE | `/libros/{id}` (baja lógica) | 204, 404 |
| POST | `/libros/{id}/reponer` | 200, 404, 409, 422 |
| GET | `/libros/{id}/movimientos` | 200, 404 |

Cuerpo de ejemplo `POST /libros`: `{"isbn":"978-950-00-0006-6","titulo":"Los que aman, odian","precio":"21000.00","stock_inicial":4,"editorial_id":1,"genero_id":1,"autores":[{"autor_id":3,"rol":"coautor","orden":1},{"autor_id":4,"rol":"coautor","orden":2}]}`.

## Épica 5 — Usuarios y roles (ADMIN, grupo protegido) — módulo `usuarios`
| Método | Ruta | Códigos |
|---|---|---|
| POST | `/usuarios` (alta de personal, con contraseña provisoria) | 201, 409, 422 |
| GET | `/usuarios/{id}/roles` | 200, 404 |
| POST | `/usuarios/{id}/roles` (con vencimiento opcional) | 201, 404, 409, 422 |
| DELETE | `/usuarios/{id}/roles/{rol}` | 200, 404, 409 |
| GET | `/eventos` (`page`, `size`) | 200, 422 |

## Épica 6 — Clientes (VENDEDOR, ADMIN)
| Método | Ruta | Códigos |
|---|---|---|
| POST | `/clientes` | 201, 409, 422 |
| GET, PATCH | `/clientes/{id}` (con su perfil) | 200, 404, 409, 422 |
| POST | `/clientes/{id}/perfil` | 201, 404, 409 |
| GET | `/clientes/{id}/ventas` | 200, 404 |

## Épica 7 — Ventas
| Método | Ruta | Quién | Códigos |
|---|---|---|---|
| POST | `/ventas` (con `renglones`) | VENDEDOR, ADMIN | 201, 409, 422 |
| GET | `/ventas` (`page`, `size`) | VENDEDOR, ADMIN | 200, 422 |
| GET | `/ventas/{id}` | personal o cliente dueño | 200, 403, 404 |
| GET | `/mis-ventas` (`page`, `size`) | Autenticado | 200, 422 |

Cuerpo `POST /ventas`: `{"cliente_id":2,"renglones":[{"libro_id":1,"cantidad":2},{"libro_id":4,"cantidad":1}]}` (no viajan precio, total ni fecha).

Toda ruta del grupo protegido responde además **401 sin sesión** y **403 con cambio de contraseña pendiente**.

## Historias clave (criterios)
### US-001 — Auto-registro (RN-01, RN-02)
Como visitante quiero registrarme para consultar mis compras. CA: crea usuario + rol CLIENTE + ficha de cliente en un solo UoW; email de usuario repetido -> 409; email de cliente existente -> 409 sin apropiarse de la ficha y sin filas sueltas; el cuerpo rechaza `rol` (`extra=forbid`); contraseña > 72 bytes -> 422.
### US-002 — Login seguro (RN-07, RN-08)
CA: cookie HttpOnly/SameSite=Lax/Max-Age, sin token en el cuerpo; correo inexistente y contraseña errónea dan 401 idéntico y tiempo parecido; 6.º intento fallido -> 429 + `Retry-After` en pocos ms; cada intento (ok o fallido) queda en `intento_acceso`.
### US-003 — Revocación efectiva (RN-04, RN-05)
CA: admin revoca rol a un vendedor con sesión abierta y la misma cookie da 403 en la petición siguiente; `/auth/yo` muestra roles vigentes vs. los del token; vencimiento pasado o sin zona -> 422; admin no se revoca su ADMIN -> 409.
### US-004 — Cambio obligatorio de contraseña (RN-06)
CA: `nuevo@example.com` bloqueado (403) salvo `/auth`; tras cambiar, `debe_cambiar_password` queda false y la misma cookie sirve en rutas protegidas (200).
### US-005 — Registrar venta (RN-09, RN-10)
CA: 201 con precios copiados y total; baja el stock; un movimiento por renglón; aviso en el log después de la respuesta; stock insuficiente -> 409 sin escrituras; cliente/libro inexistente o libro dado de baja -> 409 sin escrituras.
### US-006 — Ciclo de vida del libro (RN-11, RN-13)
CA: reponer -> 200 con movimiento; baja -> 204 y desaparece del catálogo; mismo ISBN vigente -> 201 tras la baja; segundo vigente con ese ISBN -> 409; la venta vieja sigue mostrando el título.
### US-007 — Ver mis ventas (RN-14)
CA: la cliente ve su venta (200) y no la ajena (403).
### US-008 — Lectura sin N+1 (Ej. 8)
CA: detalle de venta con 2 y con 4 renglones emite la misma cantidad de consultas (con `SQL_ECHO=true`).
### US-009 — Despliegue (Ej. 9-10)
Ver `07_flujos_principales.md` (flujo 7) y `12_entregables_del_parcial.md`.
