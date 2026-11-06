# Proposal

## Why

El PDF exige que el proyecto se ponga en marcha con `python seed.py` («es parte de la puesta en marcha y no un extra para probar»), que `test/` traiga un `.http` por caso C-01..C-16 con la respuesta esperada en comentario y precedido de `python seed.py`, que `evidencia/` tenga la captura de C-14 y las consultas de C-15, y que el `README.md` permita levantar el proyecto desde cero. Hoy `parcial/` no tiene `seed.py` (sólo el `test/seed.sql` del TP, sin usuarios, roles ni movimientos, con datos que contradicen el PDF: IN-02/IN-03), los `.http` existentes son los del TP (numeración vieja, IN-04) más archivos por change que dependen de usuarios `c0x.` creados a mano y de limpiezas por psql, la evidencia C-15 se tomó sobre datos de prueba `c08.` y el README describe el TP Cap 1-4. Sin esto los casos C no son reproducibles y la entrega queda incompleta (requisito del zip y evidencia de los Ej. 3-8).

## What Changes

- **Nuevo `parcial/seed.py`** (`python seed.py` desde `parcial/`): en una sola transacción vacía todas las tablas de la aplicación con `TRUNCATE ... RESTART IDENTITY CASCADE` (DD-10; el disparador de sólo agregado no se toca) y carga los datos iniciales del PDF con ids conocidos: 3 editoriales, 3 géneros, 6 autores; 5 libros en el orden del ejemplo del PDF (1 Rayuela 25000.00, 2 Antología de la literatura fantástica 30000.00, 3 Ficciones 22000.00, 4 Respiración artificial, 5 Bestiario) con stock final 10/5/8/3/1; usuarios `admin`, `admin2` (ADMIN), `vendedor` (VENDEDOR), `ana` (CLIENTE), `nuevo` (VENDEDOR con cambio obligatorio) con contraseñas de mentira hasheadas con bcrypt; clientes Lucía Fernández (con perfil) y Tomás Ríos sin usuario, Ana Paz con `ana@example.com`; venta 1 de Lucía (1 Rayuela + 2 Ficciones = 69000.00) registrada por `vendedor`; un movimiento «Stock inicial» por libro (Rayuela 11, Ficciones 10) y dos «Venta» (-1, -2), escritos por el punto único de escritura del stock, de modo que `stock == SUM(movimientos)` en los cinco libros; una única línea de `evento_seguridad` con actor `SISTEMA`: «Carga de los datos iniciales». Idempotente: correrlo de nuevo deja exactamente el mismo estado.
- **Casos C reescritos sobre el seed**: un archivo `parcial/test/C-NN_<tema>.http` por caso C-01..C-16 (C-14 sigue en `solo_agregado.sql`), cada uno autocontenido tras `python seed.py`, con los usuarios e ids del seed, varias sesiones (`# @name`, `# @no-cookie-jar`, `Cookie: {{login.response.headers.Set-Cookie}}`) y la respuesta esperada en comentario; las comprobaciones que sólo se ven en la base (fila suelta, `intento_acceso`, `stock == SUM`) se dejan como consultas psql comentadas.
- **BREAKING (sólo pruebas)**: se retiran `test/seed.sql`, los `.http` del TP (`C-01..C-08` con la numeración vieja, incluido `C-07_consultas_fijas.http`), la carpeta `test/C-07_CapturasPantalla/` y los archivos por change `auth.http`, `autorizacion.http` y `libros_clientes_ventas.http` (dependen de usuarios `c0x.` y limpiezas manuales; su contenido útil se reubica en el caso que corresponde). `C-15_detalle_consultas_fijas.http` se reescribe sobre el seed.
- **Evidencia**: `parcial/evidencia/C-15_consultas_detalle_venta.txt` se regenera tras `python seed.py` (venta 1 de 2 renglones y una venta nueva de 4); nuevo `parcial/evidencia/C-14_solo_agregado.txt` con la salida de psql de `test/solo_agregado.sql`.
- **`parcial/README.md` reescrito** para el parcial: integrantes (Q-06), entorno virtual, dependencias, `.env` desde `env.example` y cómo generar `JWT_SECRET_KEY`, `alembic upgrade head`, `python seed.py`, arranque (`uvicorn main:app`), usuarios del seed, tabla de casos C-01..C-16 con su archivo y la evidencia; verificado siguiéndolo desde una base vacía.
- Sin cambios en la aplicación (`app/`, `main.py`), en las migraciones ni en `despliegue/`.

## Capabilities

### New Capabilities
- `datos-iniciales`: el script `seed.py` que deja la base en el estado inicial conocido del PDF (contenido, ids, coherencia de stock y movimientos, línea `SISTEMA`, idempotencia, contraseñas sólo hasheadas).
- `casos-prueba`: los casos C-01..C-16 como archivos `.http` reproducibles tras `python seed.py`, con respuesta esperada en comentario y varias sesiones, y la carpeta `evidencia/` (C-14 y C-15).
- `guia-puesta-en-marcha`: el `README.md` de `parcial/` con integrantes y los pasos desde cero hasta el servidor con datos iniciales.

### Modified Capabilities
- `lecturas-relaciones`: la evidencia C-15 se toma sobre los datos iniciales (venta 1 de 2 renglones y una de 4 creada en el caso) y la no regresión se comprueba con los casos C-01..C-16 en lugar de los `.http` por change.
- `migraciones-esquema`: el caso C-14 deja su captura de psql en `parcial/evidencia/`.

## Impact

- Nuevos: `parcial/seed.py`, `parcial/test/C-01..C-16_*.http` (salvo C-14), `parcial/evidencia/C-14_solo_agregado.txt`.
- Reescritos: `parcial/README.md`, `parcial/test/C-15_detalle_consultas_fijas.http`, `parcial/evidencia/C-15_consultas_detalle_venta.txt`.
- Retirados: `parcial/test/seed.sql`, `parcial/test/C-0{1..8}_*.http` del TP, `parcial/test/C-07_CapturasPantalla/`, `parcial/test/{auth,autorizacion,libros_clientes_ventas}.http`.
- Sin cambios: `parcial/app/**`, `parcial/main.py`, `parcial/migrations/**`, `requirements.txt`, `env.example`, `despliegue/**` (conserva su propio `test/seed.sql`).
- Decisiones del grupo pendientes: Q-06 (integrantes) y Q-05 (contraseñas del seed; se propone un valor por defecto).
