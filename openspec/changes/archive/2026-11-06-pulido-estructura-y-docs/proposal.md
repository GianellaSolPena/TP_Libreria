# Proposal

## Why

La auditoría post-entrega (2026-11-06) dejó observaciones menores de estructura y documentación que conviene cerrar antes de rearmar el zip (F-04): la duda de si `parcial/app/core/dependencies.py` respeta la «Estructura obligatoria» del PDF (importa de `app.modules.usuarios`), comandos de `despliegue/DEPLOY.md` en una sola línea muy larga (algunos con espacios en blanco donde había saltos de línea), una carpeta suelta `app/` en la raíz del repo y un `parcial/README.md` que todavía no menciona el caso extra de RN-15 (F-01) ni la evidencia reproducible que agrega F-02. Ninguna es un incumplimiento del PDF; son pulido de entrega.

## What Changes

- **Decisión de estructura (sin mover código)**: `app/core/dependencies.py` se queda en `app/core/`. El PDF (p. 8) lo lista con ruta fija `app/core/dependencies.py` y contenido «Usuario actual, roles vigentes, control del cambio obligatorio y `requiere_rol`»; leer el usuario y sus roles vigentes obliga a usar el modelo y el repositorio de `usuarios`. Se documenta como **DD-11** en `knowledge-base/09_decisiones_y_supuestos.md` y se corrige la nota vieja de `knowledge-base/08_arquitectura_propuesta.md` (§Estructura dice que `main.py` «hoy vive en `app/main.py`», ya no es cierto desde C-02).
- **`despliegue/DEPLOY.md`**: los comandos largos (`tar … | ssh …`, los `docker run` y el `docker exec … psql …`) se parten en varias líneas con `\`, sin cambiar ni un argumento. Sólo documentación; la lógica de `despliegue/` no se toca.
- **Carpeta `app/` suelta en la raíz**: al proponer (2026-11-06) **ya no existe** (`ls app` → no existe; `git status --ignored` no la lista). La tarea queda como verificación: si reaparece y sólo contiene `__pycache__`, se borra; si tiene otra cosa, se frena y se consulta.
- **`parcial/README.md`**: agrega la fila del caso extra `RN-15_caracter_nulo.http` a la tabla de casos y menciona en «Estructura» y «Casos de prueba» los archivos de evidencia nuevos de `parcial/evidencia/` que produce F-02 (**depende de F-02**: esa parte se hace después de que F-02 deje sus archivos).
- **Opcionales (no los pide el PDF; separados, no bloquean el cierre)**: `.http` extra de RN-03 (rol ya vigente → 409) y de token vencido (401); escapar `%` y `_` en la búsqueda por título de `GET /libros`.

## Capabilities

### New Capabilities
<!-- ninguna -->

### Modified Capabilities
- `guia-puesta-en-marcha`: el requisito «Guía de los casos de prueba y la evidencia» pasa a exigir también los casos extra (RN-15) y todos los archivos de `parcial/evidencia/`, no sólo C-14 y C-15.
- `despliegue-vps`: el requisito «DEPLOY.md completo» exige además que los comandos largos estén partidos con `\` y se puedan copiar y pegar tal cual.

## Impact

- **Documentación**: `parcial/README.md`, `despliegue/DEPLOY.md`, `knowledge-base/09_decisiones_y_supuestos.md` (DD-11), `knowledge-base/08_arquitectura_propuesta.md` (nota de §Estructura).
- **Código**: ninguno en el alcance obligatorio. Los opcionales tocarían `parcial/test/` (archivos `.http` nuevos) y, el del escape, `parcial/app/modules/libros/repository.py`.
- **API / esquema / migraciones**: sin cambios.
- **Coordinación**: F-02 `evidencia-casos-reproducible` corre en paralelo y crea archivos en `parcial/evidencia/`; la tarea del README que los menciona espera a F-02. Este change no edita `CHANGES.md` (lo marca el archivado).
- **Fuera de alcance**: rearmar el zip (F-04), mover `dependencies.py`, cambiar la lógica de `despliegue/`.
