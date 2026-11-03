# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — Strict TDD con pytest en cada change
**Decisión**: todo change se implementa con strict TDD (RED/GREEN/TRIANGULATE/REFACTOR) usando **pytest**, además de los archivos `.http` y `test/solo_agregado.sql` que el PDF exige.
**Contexto**: el PDF sólo pide casos `.http` con la respuesta esperada en comentario y el `.sql` del caso C-14; no pide tests automatizados. El usuario decidió agregarlos.
**Alternativas consideradas**: sólo `.http` (lo mínimo del PDF).
**Justificación**: los invariantes del parcial (rollback total de ventas, `stock == SUM(movimientos)`, disparador, 401/403, 429) se verifican mejor con tests repetibles.
**Trade-offs aceptados**: hace falta un **PostgreSQL 16 descartable** (Docker Desktop) para correr los tests; SQLite no sirve (índices únicos parciales, disparadores, `timestamptz`). Añade dependencias de test (pytest, pytest-asyncio, httpx, etc.). Los `.http` siguen siendo entregable obligatorio. El zip no debe incluir `.venv` ni `__pycache__` ni `.env` (cuidar `.pytest_cache`).

### DD-02 — Modificar el TP existente, no reescribir
**Decisión**: el parcial se resuelve sobre el código del TP Cap 1-4 ya entregado (`app/`, `migrations/`, `test/`). **Contexto**: el PDF dice "El grupo parte de su propio TP entregado". **Justificación**: reaprovechar modelos, migraciones 0001-0002, routers y casos C-01..C-08. Brecha en `11_brecha_tp_vs_parcial.md`.

### DD-03 — Dos proyectos en el zip
**Decisión**: `parcial/` (todo menos despliegue) y `despliegue/` (TP Cap 1-4 congelado + Docker). Origen: formato de entrega del PDF. El despliegue **no** lleva ninguna de las modificaciones del parcial. Hay que **conservar una copia del TP Cap 1-4 intacto** (commit `e337710` y anteriores) antes de modificar nada, para armar `despliegue/`.

### DD-04 — Orden de las migraciones (PDF)
0003 con `--autogenerate` (leída, comentada) y 0004 a mano (disparador). Sin `create_all`.

### DD-05 — Intento de acceso fuera de la transacción de la petición (PDF)
Excepción deliberada, documentada con un comentario de tres puntos (qué hace distinto, por qué, costo).

### DD-06 — Sólo-agregado con disparador; sin segundo mecanismo (PDF)
Un solo rol de base; el mecanismo por permisos no se pide.

### DD-07 — Cookie y no `Authorization` (PDF)
Login tradicional con cookie; no se invalidan sesiones al cambiar la contraseña.

### DD-08 — `main.py` y `seed.py` en la raíz de `parcial/` (letra del PDF, p. 8)
La tabla "Estructura obligatoria" lista `main.py` y `seed.py` sin prefijo, mientras todo lo demás lleva `app/...`. Por defecto se sigue la letra del PDF: `parcial/main.py` (arranque `uvicorn main:app`); `app/main.py` del TP se mueve en C-03. `despliegue/` no cambia (`app.main:app`). Q-03 queda para confirmar con la cátedra; si responde otra cosa, se revierte en C-03.

### DD-09 — `intento_acceso` con un UoW propio (Ej. 7 + capas)
La sesión propia del intento se crea desde la fábrica de `app.state` dentro de un UoW/repositorio dedicado que construye el router, así el servicio de login sigue sin tocar sesiones y la excepción queda en un solo lugar con su comentario de tres puntos.

### DD-10 — Vaciar tablas con `TRUNCATE`
El disparador de sólo agregado rechaza DELETE (RN-12); `seed.py` y la limpieza de tests usan `TRUNCATE ... RESTART IDENTITY CASCADE`, que no dispara los triggers de fila. No se debilita el disparador.

## Supuestos inferidos

### SU-01 — Entorno de pruebas local
**Supuesto**: el grupo corre PostgreSQL 16 en Docker Desktop (Windows 11). **Origen**: instrucción del usuario. **Riesgo si es falso**: tests no ejecutables. **Validar**: `docker run postgres:16` disponible. (Nota: durante la generación de esta KB `python` no estaba en el PATH del shell de Git Bash; sí `docker` 29.9.2.)

### SU-02 — El nombre "libreria" para imagen y contenedor
**Supuesto**: imagen `libreria`, contenedor `--name libreria`, tal como en los comandos del PDF. **Origen**: PDF (ejemplos `docker run ... libreria`, `docker exec libreria`).

### SU-03 — Respuestas del TP actual válidas hasta ser reemplazadas
**Supuesto**: los 409 con mensaje propio del TP se conservan y se adaptan a la nueva capa de traducción. **Riesgo**: mensajes inconsistentes. **Validar**: test por servicio.

### SU-04 — Orden de los renglones y `precio_unitario`
**Supuesto**: se mantienen los nombres `renglon_venta.precio_unitario` y `venta.total` del TP (el PDF no los cambia y dice que "precio y total nunca viajan en el cuerpo").

### SU-05 — Extracción del PDF — **RESUELTO**
Las tablas (modelo p. 5-6, RN p. 7-8, estructura p. 8-9, endpoints p. 16-18, seed p. 19-20, casos p. 21-23) se re-extrajeron con `pdftotext -table` (columnas respetadas) y la Figura 1 se leyó renderizando la p. 5 a imagen. Todo emparejamiento RN ↔ garante y ruta ↔ método ↔ rol ↔ códigos quedó verificado (ver `13_auditoria_vs_pdf.md`).

### SU-06 — Secciones del material de cátedra
**Supuesto**: las referencias "sección 4.5, 5.5, 6.7, 6.9, ..." apuntan a apuntes de la materia que **no** están en el repo; sólo se conoce lo que el PDF transcribe de ellas.
