# Entregables del Parcial

Entrega: **una por grupo**, un único `.zip` que sube **un solo integrante** al campus (tarea de entrega: `https://campustest.frm.utn.edu.ar/mod/assign/view.php?id=1915`). Nombre: `Parcial_Cap1a6_<NombreDelGrupo>.zip` (nombre del grupo: pendiente, Q-01). Fecha límite: se publica en el campus (Q-13).

## Puntaje por ejercicio (total 100)
| Ej. | Título | Puntos | Qué se mira (criterios de evaluación) |
|---|---|---|---|
| 1 | Proyecto, configuración y ciclo de vida | **6** | Estructura, Settings sin secretos por defecto, motor y fábrica creados en el lifespan, `get_session`, salud |
| 2 | Modelos, relaciones y migraciones | **10** | Restricciones, índices únicos parciales, navegación, dos migraciones nuevas (una a mano), upgrade y downgrade |
| 3 | Contratos y CRUD | **8** | Contratos separados, `extra="forbid"`, códigos, ninguna entrada inválida en 500, PATCH parcial, envoltorio y paginación (sec. 2.9) |
| 4 | Autenticación | **14** | bcrypt fuera del bucle y con semáforo, orden del login, límite, hash ficticio, cookie HttpOnly |
| 5 | Autorización | **12** | 401 y 403, roles vigentes en la base, autoprotección, dos grupos de rutas, cambio obligatorio, lo propio |
| 6 | Repositorios y Unit of Work | **16** | Dos jerarquías, clase del modelo, `flush` y no `commit`, precarga en el repositorio, quién crea/abre/confirma/cierra, operaciones de varias escrituras, un solo punto de escritura del stock |
| 7 | Integridad: sólo agregado e intento de acceso | **10** | Disparador de sólo agregado; intento de acceso en su propia sesión con su comentario; eventos en la misma transacción |
| 8 | Lecturas sin N+1 y asincronía | **6** | Consultas fijas en el detalle; ninguna llamada bloqueante; aviso en segundo plano visible |
| 9 | Contenedor: la imagen | **11** | Sobre el TP Cap 1-4: base `python:3.12-alpine`, capas en orden, usuario sin privilegios, sin secretos, migraciones al arrancar, HEALTHCHECK, `docker run` con `--env-file` |
| 10 | Despliegue en el VPS | **7** | TP Cap 1-4 en línea en la URL declarada, DEPLOY.md completo, casos D con evidencia |

Suma: 6+10+8+14+12+16+10+6+11+7 = **100**. (Los pesos del criterio en % coinciden con los puntos.) Ej. 1-8 = 82 pts (parcial/); Ej. 9-10 = 18 pts (despliegue/).

Reglas duras: proyecto que no levanta, que no crea esquema con `alembic upgrade head` sobre base vacía, o con credenciales reales en repo/imagen/zip -> no se corrige hasta subsanar. Si el despliegue no está accesible al corregir, el criterio del VPS se evalúa sólo con DEPLOY.md y `evidencia/`, y los casos D no comprobables **no suman**.

## Contenido del .zip (dos carpetas, dos proyectos distintos)
```
Parcial_Cap1a6_<Grupo>.zip
├── parcial/                      proyecto ampliado, SIN el despliegue
│   ├── (código fuente completo: main.py, seed.py, app/...)
│   ├── requirements.txt
│   ├── env.example               todas las variables, ningún secreto
│   ├── alembic.ini               sin credenciales
│   ├── migrations/               0001..0004
│   ├── test/                     .http (casos C) + solo_agregado.sql (C-14)
│   ├── README.md                 integrantes (nombres y apellidos) + pasos desde cero
│   └── evidencia/                C-15 (consultas del detalle con 2 y con 4 renglones) + captura de psql de C-14
└── despliegue/                   TP Cap 1-4 TAL COMO SE ENTREGÓ
    ├── (código del TP) + Dockerfile + .dockerignore
    ├── env.example               forma de DATABASE_URL, sin valores reales
    ├── DEPLOY.md
    └── evidencia/                salida de cada caso D
```
**No** lleva: `.venv`, `__pycache__` (en ninguna carpeta), `.env`. Si incluye `.git`, se revisa el historial (una contraseña subida y borrada sigue ahí; se pediría cambiarla). Cuidado adicional por DD-01: `.pytest_cache`, `.env.test`, etc. fuera del zip.

### README.md de `parcial/` debe cubrir
Integrantes; entorno virtual; dependencias; `.env` con **cómo generar la clave de firma**; `alembic upgrade head`; `python seed.py`; arranque del servidor.

### DEPLOY.md debe incluir
URL pública; día y hora del despliegue; comandos `docker build` y `docker run` **completos** (con el nombre del archivo de variables, sin su contenido); cambios hechos al TP para que corra en el contenedor; cómo se actualiza (rebuild, `docker rm -f`, mismo `docker run`; los datos no se pierden). Más: si se construyó en el servidor o se llevó la imagen.

## Dockerfile (Ej. 9) — checklist
- [ ] `FROM python:3.12-alpine` (base 74,7 MB < 100 MB; `slim` 180 MB no cumple; sin compilador: las deps se instalan sin compilar)
- [ ] Copiar e instalar `requirements.txt` **antes** del código, con `--no-cache-dir`
- [ ] Usuario sin privilegios + `USER`
- [ ] Sin secretos: `.dockerignore` excluye `.env`, `.venv`, `.git`, `__pycache__`; sin URL/contraseña de base en el Dockerfile (entran por variables al `docker run`)
- [ ] Al arrancar: `alembic upgrade head` y después `uvicorn app.main:app --host 0.0.0.0` (puerto 8000), encadenados de modo que **si Alembic falla el contenedor termina con error** (p. ej. `sh -c "alembic upgrade head && exec uvicorn ..."`); no se tragan errores (D-05)
- [ ] El límite de 100 MB es de la **imagen base** (`python:3.12-alpine` 74,7 MB); la del proyecto puede ser mayor (D-01)
- [ ] `HEALTHCHECK` sobre `GET /health/ready` con `wget` a `http://127.0.0.1:8000/...` (no `localhost`)
- [ ] Se agregan al TP **sólo** Dockerfile y .dockerignore; la lógica no se toca (excepto defectos propios, anotados en DEPLOY.md: IN-06, IN-07)
- [ ] No Docker Compose
- [ ] `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file <archivo> libreria`; `--add-host=host.docker.internal:host-gateway` en Linux si la base está en el host; `DATABASE_URL` nunca con `localhost`; `SQL_ECHO=false` en el env-file

## Casos de prueba: C (sobre `parcial/`)
Antes de cada `.http` se corre `python seed.py`. Cada petición lleva su respuesta esperada en un comentario. REST Client con varias sesiones: `# @name loginAdmin`, `# @no-cookie-jar`, `Cookie: {{loginAdmin.response.headers.Set-Cookie}}`.
| Caso | Qué se demuestra | Resultado esperado |
|---|---|---|
| C-01 | Parámetro de ruta no entero, con sesión iniciada | 422, sin ejecutar el handler |
| C-02 | Registro; correo repetido de usuario y de cliente | 201; 409 con mensaje propio; el registro rechazado no deja fila suelta |
| C-03 | La cookie del login | `Set-Cookie` con HttpOnly, SameSite=Lax y Max-Age; cuerpo sin token; sin cookie o con `Authorization: Bearer`, 401 |
| C-04 | Correo existente con contraseña mala, y correo inexistente | 401 con el mismo cuerpo y tiempo parecido |
| C-05 | Seis intentos fallidos seguidos | El sexto, 429 con `Retry-After` y en pocos ms; los cinco fallos están en `intento_acceso` |
| C-06 | 401 contra 403, y lo propio | Sin sesión 401; un vendedor que crea un libro 403; la cliente ve su venta (200) y no la ajena (403) |
| C-07 | Revocar un rol con la sesión abierta; vencimientos inválidos | La misma cookie, 403 en la petición siguiente; `/auth/yo` muestra la diferencia; la fila revocada sigue; vencimiento pasado o sin zona -> 422 |
| C-08 | Autoprotección | El administrador no se revoca su ADMIN: 409 |
| C-09 | Cambio obligatorio | Bloqueado (403) salvo `/auth`; después del cambio `debe_cambiar_password=false` y la misma cookie sirve (200) sin iniciar sesión de nuevo |
| C-10 | Venta válida con dos renglones | 201 con precios copiados y total; stock baja; un movimiento por renglón; aviso en el log después de la respuesta |
| C-11 | Venta con Rayuela (1 ej., alcanza) y Bestiario (2 ej., hay 1) | 409; no hay venta nueva, ni descuentos, ni movimientos; stock de Rayuela sigue en 10; suma de movimientos = stock en los cinco libros |
| C-12 | Venta con cliente o libro inexistente, o libro dado de baja | 409 en los tres, sin escrituras |
| C-13 | Reponer; dar de baja; volver a cargar el mismo ISBN | Reposición 200 con movimiento; baja 204; deja de aparecer en el catálogo; alta con mismo ISBN 201; segundo vigente 409; la venta vieja muestra el título |
| C-14 | UPDATE y DELETE sobre `movimiento_stock` en psql (`test/solo_agregado.sql`) | Ambos rechazados por el disparador (captura en `evidencia/`) |
| C-15 | Detalle de venta con 2 y con 4 renglones | Misma cantidad de consultas en la consola (con `SQL_ECHO=true`; evidencia) |
| C-16 | Búsqueda con `' OR '1'='1`; paginación con filtro; PATCH parcial; PATCH del stock | Lista vacía total 0; `titulo=ficc&size=1` total 1, pages 1, `page=2` -> 422; `size=500` -> 422; sólo cambia lo enviado; PATCH con `stock` -> 422 |

## Casos de prueba: D (sobre el TP Cap 1-4 desplegado; salida en `despliegue/evidencia/`)
| Caso | Qué se demuestra | Resultado esperado |
|---|---|---|
| D-01 | `docker images` con la imagen base y la del proyecto | `python:3.12-alpine` < 100 MB; el Dockerfile parte de ella |
| D-02 | Servidor limpio: `docker build` y `docker run`; luego `docker ps` | Contenedor `healthy`; en `docker logs`, migraciones aplicadas al arrancar |
| D-03 | Desde afuera del VPS, URL pública: `GET /health/ready`, `GET /libros/` con datos iniciales, `POST /ventas/` con el cuerpo de ejemplo del TP | 200; 200 con la lista; 201 con precios copiados y total calculado |
| D-04 | `docker rm -f libreria` y el mismo `docker run` otra vez | Vuelve a `healthy`; los datos siguen; las migraciones no se repiten |
| D-05 | Correr la imagen sin `DATABASE_URL` | El contenedor termina con error (el TP no trae dirección por defecto) |
| D-06 | Contenido de la imagen | No hay `.env` (`docker run --rm --entrypoint ls <imagen> -a /app`); `docker run --rm --entrypoint env <imagen>` no muestra `DATABASE_URL` ni contraseña |
| D-07 | Usuario del proceso | `docker exec libreria id` no es root |
| D-08 | La venta registrada en D-03 | El aviso del comprobante aparece en `docker logs libreria` después de la línea de la respuesta |

## Verificación de invariantes (para tests pytest, DD-01)
- `stock == SUM(movimiento_stock.cantidad)` por libro, tras cada caso de venta (C-10, C-11, C-12).
- Rollback total en venta fallida (ni venta, ni renglones, ni descuentos, ni movimientos).
- `intento_acceso` persiste aunque la petición falle.
- Disparador rechaza UPDATE/DELETE incluso desde SQL directo.
- Cantidad fija de consultas en detalle de venta (2 vs 4 renglones).
