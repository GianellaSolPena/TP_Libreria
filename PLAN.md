# Plan de resolución · TP Librería (Programación III, Unidades 1-4)

Estructura a construir (ya creada):

```
TP_Libreria/
├── app/
│   ├── main.py                  # App, lifespan, registro de routers
│   ├── core/
│   │   ├── config.py            # Lectura de DATABASE_URL desde .env
│   │   └── database.py          # Motor, fábrica de sesiones, get_session
│   └── modules/
│       ├── health/              # models · schemas · service · router
│       ├── editoriales/
│       ├── generos/
│       ├── autores/
│       ├── libros/              # incluye LibroAutor
│       ├── clientes/            # incluye PerfilCliente
│       └── ventas/              # incluye RenglonVenta
├── migrations/                  # Alembic (plantilla asincrónica) + versions/
├── test/                        # Archivos .http con casos C-01..C-08
├── requirements.txt
├── env.example                  # Forma de DATABASE_URL, sin secretos
└── README.md
```

---

## Ejercicio 1 · Proyecto, conexión y ciclo de vida (10 %)

1. Crear `requirements.txt` con: fastapi>=0.111, sqlmodel>=0.0.24, sqlalchemy[asyncio]>=2.0,
   asyncpg>=0.30, alembic>=1.13, python-dotenv>=1.0, uvicorn (de `fastapi[standard]`).
2. `app/core/config.py`: leer `DATABASE_URL` con `dotenv` (`load_dotenv()`); fallar con mensaje
   claro si no existe. No hardcodear credenciales.
3. `app/core/database.py`:
   - `create_async_engine(DATABASE_URL, echo=configurable)`.
   - `sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)` (sección 4.5).
   - `get_session()`: dependencia async que cede la sesión y hace `commit`/`close`.
4. `app/main.py` con `lifespan`: dentro de `startup` se crea el motor y se guarda en
   `app.state.engine` / `app.state.session_factory`; en `shutdown`, `await engine.dispose()`
   (sección 1.9). `create_app(lifespan=...)`.
5. Registrar todos los routers (`include_router`) y `GET /health/live` (responde
   `{"estado": "vivo"}` sin tocar la base) y `GET /health/ready` (ejecuta `SELECT 1` vía
   `text("SELECT 1")`; 200 si responde).
6. Verificar: `uvicorn app.main:app` levanta y `/docs` muestra los endpoints.

## Ejercicio 2 · Modelos, restricciones y relaciones (25 %)

1. En cada `modules/<módulo>/models.py` crear clases `SQLModel, table=True` con `__tablename__`
   exacto (nombres obligatorios del TP):
   - `editorial(id, nombre UNIQUE, pais)`
   - `genero(id, nombre UNIQUE)`
   - `autor(id, nombre, nacionalidad)`
   - `libro(id, isbn UNIQUE, titulo, precio NUMERIC(10,2), stock, editorial_id FK, genero_id FK nullable)`
     + `CheckConstraint(precio > 0)`, `CheckConstraint(stock >= 0)`
   - `libro_autor(libro_id, autor_id, rol, orden)` → PK compuesta `(libro_id, autor_id)`,
     `CheckConstraint(orden >= 1)`, `CheckConstraint(rol IN ('autor','coautor','traductor','ilustrador'))`
   - `cliente(id, nombre, email UNIQUE)`
   - `perfil_cliente(id, cliente_id FK UNIQUE, telefono, direccion)` → uno a uno
   - `venta(id, cliente_id FK, fecha timestamptz, total NUMERIC(12,2))` + `CheckConstraint(total >= 0)`
   - `renglon_venta(id, venta_id FK, libro_id FK, cantidad, precio_unitario NUMERIC(10,2))`
     + `CheckConstraint(cantidad > 0)`, `CheckConstraint(precio_unitario > 0)`
2. Reglas de decisión del lado de la FK:
   - Agregación (libro→editorial, libro→género): FK en `libro`.
   - Asociación (venta→cliente): FK en `venta`.
   - Composición (renglón→venta): FK en `renglon_venta`.
   - Muchos a muchos con datos: tabla intermedia `libro_autor` con PK compuesta.
   - Uno a uno (perfil): FK en `perfil_cliente` + `unique=True` (UNIQUE en `cliente_id`).
3. Índice en **cada** FK (`index=True` en la columna) — PostgreSQL no los crea solo (4.10).
4. Navegación en **los dos extremos** con `Relationship(back_populates=...)`:
   - `Libro.editorial`, `Editorial.libros`; `Libro.genero`, `Genero.libros`
   - `Libro.autorias` → lista de `LibroAutor`; `LibroAutor.libro` y `LibroAutor.autor`;
     `Autor.autorias` (navegación libro→autores: `libro.autorias[i].autor`)
   - `Cliente.perfil` → **objeto, no lista** (`Relationship(uselist=False, back_populates=...)`)
     y `PerfilCliente.cliente`
   - `Venta.cliente` / `Cliente.ventas`; `Venta.renglones` / `RenglonVenta.venta`;
     `RenglonVenta.libro` / `Libro.renglones`
5. Todo el dinero con `Decimal` (`sa_type=Numeric(10,2)` / `Numeric(12,2)`), nunca `float`.
6. Imports de `Relationship`/`ForeignKey` desde `sqlmodel` (o `sqlalchemy.orm` donde haga falta).

## Ejercicio 3 · Migraciones (10 %)

1. `alembic init migrations` con **plantilla asincrónica** (ajustar `env.py` con
   `async_engine_from_config` + `run_async`); `sqlalchemy.url` leído desde `DATABASE_URL` del `.env`
   (nada de credenciales en `alembic.ini`).
2. Primera migración `--autogenerate` con **todas las tablas menos `genero`** (guardar
   `app/main.py` sin importar aún `genero` o excluirlo temporalmente del metadata).
3. Segunda migración `--autogenerate` que agrega la tabla `genero` y la columna `libro.genero_id`.
4. **Leer cada archivo generado** en `migrations/versions/`; si algo está mal (orden, tipos,
   índices faltantes), corregirlo a mano y dejar un comentario explicando el porqué.
5. Probar sobre base vacía:
   - `alembic upgrade head` → se crean todas las tablas.
   - `alembic downgrade -1` → solo quita lo de la última migración.
   - `alembic upgrade head` → vuelve al estado completo.
6. No usar `create_all` en ninguna parte.

## Ejercicio 4 · Contratos y CRUD (15 %)

1. En cada `schemas.py`: `Create` (sin `id`), `Update` (todos opcionales), `Read` (con `id`).
2. En cada `service.py`: alta, listado paginado, lectura por id, patch parcial
   (`model_fields_set` / `exclude_unset`), traducción de `IntegrityError` → mensaje propio (RN-12).
3. En cada `router.py`:
   - `async def` siempre; `Depends(get_session)`; `response_model` declarado.
   - Códigos: 201 crear, 404 no existe, 409 base rechaza (UNIQUE/FK), 422 contrato.
   - Listados: `limit: int = Query(20, ge=1, le=100)`, `offset: int = Query(0, ge=0)` (RN-10).
   - Búsqueda por título: `titulo: str | None = Query(None)` con `ilike` parametrizado,
     **nunca** SQL armado (RN-11 / C-08).
4. `PATCH` solo actualiza campos enviados (`exclude_unset`) y devuelve 200.
5. Endpoints mínimos según tabla de "Endpoints de referencia" (health, editoriales, generos,
   autores, libros, clientes, ventas).

## Ejercicio 5 · Altas con relaciones: ids y datos (20 %)

1. `POST /libros/` (agregación + muchos a muchos con datos):
   - `LibroCreate` lleva `editorial_id`, `genero_id` (opcional) y `autores: list[LibroAutorCreate]`
     donde `LibroAutorCreate = {autor_id, rol, orden}`.
   - **Sin** `if` previos de existencia: se inserta y, si la base rechaza la FK, `IntegrityError`
     → 409 con mensaje propio (C-04).
2. `POST /ventas/` (asociación + composición):
   - `VentaCreate = {cliente_id, renglones: [{libro_id, cantidad}]}` — no viajan precio, total ni fecha.
   - Dentro de una misma sesión/transacción: crear `Venta`, por cada renglón leer el libro
     (RN-06: precio copiado del libro), acumular `total = Σ cantidad × precio_unitario` (RN-07).
   - Validar RN-05 en el DTO: ≥1 renglón y sin libro repetido → 422.
   - Responder 201 con cliente y renglones incluidos (ver ejemplo JSON del TP).
3. `POST /clientes/{id}/perfil`: alta de uno a uno; segundo perfil → 409 (UNIQUE, RN-09 / C-03).

## Ejercicio 6 · Lecturas sin N+1 (10 %)

1. Relaciones a uno → `selectinload`/`joinedload`... regla del TP: **`joinedload` para
   relaciones a uno** (Libro→editorial, Libro→genero, Venta→cliente, Cliente→perfil).
2. Colecciones → `selectinload` (Libro→autorias→autor, Venta→renglones→libro,
   Editorial→libros, etc.).
3. Aplicar en: detalle de libro, detalle de venta, listado de libros con editorial/género,
   detalle de cliente con perfil, y cualquier respuesta que incluya relaciones.
4. Verificar con `echo=True`: el detalle de un libro o de una venta emite **cantidad fija**
   de consultas sin importar cuántos autores/renglones haya (C-07).
5. Prohibido depender de carga perezosa: nunca tocar atributos de relación fuera de la consulta
   que los precargó.

## Ejercicio 7 · Asincronía sin bloqueos (10 %)

1. Todos los handlers `async def`; ningún `time.sleep`, `requests`, ni sesión síncrona.
2. `POST /ventas/`: declarar `background_tasks: BackgroundTasks` y agendar
   `background_tasks.add_task(avisar_comprobante, venta_id)`.
3. `avisar_comprobante` es `async def`: `await asyncio.sleep(0.5)` + `logger.info(...)`;
   corre después de enviarse la respuesta y no bloquea el event loop.
4. Revisar que el service use solo APIs asincrónicas (`await session.execute(...)`, etc.).

## Casos de prueba y entrega

1. Script de seed (p. ej. `test/seed.sql` o comando en README) que deje la base en estado inicial.
2. Archivos `.http` en `test/` cubriendo C-01 a C-08, cada uno con la respuesta esperada en comentario:
   - C-01: `GET /editoriales/abc` → 422.
   - C-02: ISBN o email repetido → 409 con mensaje propio.
   - C-03: segundo perfil del mismo cliente → 409.
   - C-04: libro con editorial/autor inexistente → 409.
   - C-05: venta con libro o cliente inexistente → 409.
   - C-06: venta válida con dos renglones → 201, precios copiados y total calculado.
   - C-07: detalle libro/venta → captura de la consola con número fijo de consultas.
   - C-08: `GET /libros/?titulo=' OR '1'='1` → 200 con lista vacía.
3. `requirements.txt`, `env.example` (sin secretos), `.env` local no versionado.
4. `README.md`: venv, dependencias, `.env`, `alembic upgrade head`, carga inicial, `uvicorn`.
5. Checklist final: sin credenciales en el repo, sin `create_all`, sin SQL armado, sin
   errores con texto de la base, `echo=True` configurable.
