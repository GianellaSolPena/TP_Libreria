# Descripción General

## Stack tecnológico (mínimos del PDF)
| Capa | Tecnología | Versión mín. | Uso |
|---|---|---|---|
| Lenguaje | Python | 3.12 | |
| Web | FastAPI | 0.111 | todos los handlers `async def` |
| Modelos | SQLModel | 0.0.24 | modelos de tabla |
| ORM/Motor | SQLAlchemy asincrónico | 2.0 | motor, sesión, carga anticipada |
| Driver | asyncpg | 0.30 | PostgreSQL async |
| BD | PostgreSQL | 16 | en el despliegue, la que ya tiene el servidor |
| Migraciones | Alembic (plantilla asincrónica) | 1.13 | |
| Config | pydantic-settings | 2.0 | clase `Settings` desde entorno / `.env` |
| Hash | bcrypt | 4.0 | contraseñas |
| Token | PyJWT | 2.8 | JWT firmado |
| Servidor | uvicorn | el que instala `fastapi[standard]` | ASGI |
| Contenedor | Docker | 20.10 | imagen del TP Cap 1-4, local y VPS |

Estado actual de `requirements.txt` del TP: fastapi, sqlmodel, sqlalchemy[asyncio], asyncpg, alembic, python-dotenv, uvicorn. **Faltan** pydantic-settings, bcrypt, PyJWT y (decisión DD-01 del grupo) pytest y sus dependencias de test.

## Arquitectura general
Dos proyectos distintos en una misma entrega:

```
parcial/      TP Cap 1-4 + todo lo del parcial (auth, UoW, repos, stock, soft delete), SIN despliegue
despliegue/   TP Cap 1-4 TAL COMO SE ENTREGÓ + Dockerfile + .dockerignore + env.example + DEPLOY.md + evidencia/
```

Capas del proyecto `parcial/` (por módulo funcional; las mismas capas en todos):

```
Request -> router.py          HTTP; construye el UoW con una dependencia, llama al servicio, traduce errores
        -> service.py         reglas de negocio; RECIBE el UoW y lo abre con `async with`; nunca lo construye
        -> unit_of_work.py    gestor de contexto async: commit al salir, rollback ante excepción, NO cierra la sesión
        -> repository.py      BaseRepository[T] / SoftDeleteRepository[T]; flush(), nunca commit(); precarga dentro del método
        -> models.py          SQLModel table=True, constraints, relaciones declaradas en los dos extremos
```

Ciclo de vida: el **lifespan** crea el motor (tamaño de pool declarado en la config) y la fábrica de sesiones y los guarda en `app.state`; calcula **una vez** el hash ficticio del login; al apagar hace `engine.dispose()`. Nada se crea al importar módulos (un recurso creado en import nace antes del event loop: anda al levantar y falla en pruebas, o al revés). `get_session` toma la fábrica de `app.state`, entrega una sesión por petición con `expire_on_commit=False` y la cierra al terminar.

`main.py` arma **dos grupos de rutas**: *abierto* (health, `/auth/*`, catálogo público) y *protegido* (lleva el control del "cambio de contraseña obligatorio" montado **una sola vez**, porque FastAPI suma dependencias y no las resta).

Las dependencias `get_usuario_actual` y `requiere_rol` reciben **la misma sesión** que el UoW (si no, cada petición autenticada tomaría dos conexiones del pool).

## Integraciones externas
| Servicio | Propósito | Tipo |
|---|---|---|
| PostgreSQL 16 (VPS de la cátedra) | Persistencia | asyncpg |
| Aviso de comprobante | Simulado: `await asyncio.sleep(0.5)` + mensaje de log | `BackgroundTasks` (en proceso) |
| VPS de la cátedra | Despliegue Docker del TP Cap 1-4 | `docker build` / `docker run`, URL pública |
| Campus UTN | Subida del `.zip` | manual (un integrante) |

## API REST
Tabla completa de endpoints en `06_funcionalidades.md`; roles en `03_actores_y_roles.md`. Grupos: `/health`, `/auth`, `/usuarios`, `/eventos`, `/editoriales`, `/generos`, `/autores`, `/libros`, `/clientes`, `/ventas`, `/mis-ventas`.

## Requisitos no funcionales (tabla del PDF)
| Requisito | Detalle |
|---|---|
| Asincronía | Todos los handlers `async def`; bcrypt siempre fuera del bucle |
| Credenciales | Ninguna contraseña ni clave de firma en el código (ni como default), en `alembic.ini`, en el repo ni en la imagen |
| Token | Sólo en cookie HttpOnly; nunca en el cuerpo ni leído de la cabecera `Authorization` |
| Esquema | Sólo con Alembic; la aplicación no usa `create_all` |
| Transacciones | Ningún repositorio confirma; ningún servicio construye su UoW; el UoW no cierra la sesión |
| Carga perezosa | Prohibida: toda relación que se lee se precarga en el repositorio |
| SQL | Nunca armado por concatenación con datos del usuario |
| Errores | Mensajes propios; nunca texto de la base ni traza; ninguna entrada inválida termina en 500 |
| Unicidad | Garantizada por la base; no se verifica con consulta previa |
| Contenedor | Imagen base `python:3.12-alpine`; no corre como root; ningún secreto en la imagen |
| Diagnóstico | Consultas visibles en consola (`SQL_ECHO=true` o equivalente) |
