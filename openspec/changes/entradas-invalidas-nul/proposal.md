# Proposal

## Why

La auditoría post-entrega (`informe-cumplimiento/index.html`, 2026-11-06) marcó como **no cumple** RN-15 / Ej. 3 («ninguna entrada inválida termina en un 500»): un carácter U+0000 en cualquier texto de entrada pasa el contrato (ningún esquema lo rechaza; el patrón del correo `^[^@\s]+@[^@\s]+$` tampoco), llega a PostgreSQL, que no admite el byte 0x00 en `text`/`varchar`, y asyncpg lanza un error de datos que `traducir_errores` (`parcial/app/core/errores.py`, l. 88-93) relanza → **500**. Reproducibles: `GET /libros?titulo=a%00b` y `POST /auth/login` con U+0000 en el correo. Es el único requisito en «no cumple» y se corrige antes de rearmar el zip (F-04).

## What Changes

- Nuevo tipo de texto reutilizable en `parcial/app/core/` que rechaza U+0000 en el contrato (422 con la forma estándar de validación de FastAPI), aplicado a **todos** los textos de entrada: cuerpos de catálogo (editoriales, géneros, autores), libros (`isbn`, `titulo`), clientes y perfil (`nombre`, `email`, `telefono`, `direccion`), auth y personal (`email`, `nombre`, contraseñas) y el parámetro de consulta `titulo` de `GET /libros`.
- Red de seguridad en `traducir_errores`: los errores de datos de la base atribuibles a la entrada (clase SQLSTATE 22 acotada a una lista explícita, p. ej. 22021 carácter fuera del repertorio) se traducen a **422** con un mensaje propio, sin texto de la base; el desborde numérico (22003 → 409) y la traducción `IntegrityError` → 409 quedan igual; cualquier otro error de la base sigue propagándose.
- Caso `.http` nuevo en `parcial/test/` (extra, no es un caso C del PDF) con los dos reproductores y otros textos con U+0000, respuesta esperada en comentario.
- Sin cambios de esquema, migraciones, rutas ni respuestas exitosas. No toca `despliegue/` ni el zip entregado.

## Capabilities

### New Capabilities
<!-- ninguna -->

### Modified Capabilities
- `errores-api`: se agregan los requisitos «carácter nulo rechazado en el contrato» (cuerpos y parámetros de consulta → 422) y «error de dato de la base traducido a 422» (red de seguridad sin texto de la base, sin alterar 409).
- `casos-prueba`: se agrega el archivo `.http` extra de RN-15 con caracteres nulos, con respuesta esperada en comentario.

## Impact

- **Código** (`parcial/` solamente): `app/core/` (tipo de texto nuevo; `errores.py`), `app/core/security.py` (`PasswordBcrypt`), `app/modules/{autores,editoriales,generos,libros,clientes,usuarios}/schemas.py`, `app/modules/libros/router.py` (query `titulo`).
- **API**: entradas con U+0000 pasan de 500 a 422; ninguna respuesta válida cambia. Login con U+0000 en el correo o la contraseña responde 422 sin registrar intento (igual que cualquier otro 422 del contrato).
- **Pruebas**: `parcial/test/RN-15_caracter_nulo.http` nuevo; regresión manual de C-01, C-02, C-03, C-04, C-05, C-16 y altas/PATCH del catálogo.
- **Fuera de alcance**: README de `parcial/` (lo actualiza F-03), evidencia reproducible (F-02), rearmado del zip (F-04), otros caracteres de control distintos de U+0000 (PostgreSQL los acepta).
