# TP Librería (Parcial Cap 1-6) — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

**Layout del repo**
- `parcial/` — copia del TP Cap 1-4 (commit `e337710`) que se evoluciona de forma incremental. `main.py` y `seed.py` van en la raíz de `parcial/`; se corre con `uvicorn main:app`.
- `despliegue/` — copia congelada del TP + Dockerfile (Ej. 9-10). Solo recibe lo de Docker/VPS.
- Raíz del repo — solo planificación (`knowledge-base/`, `openspec/`, `CHANGES.md`, README, consigna). El TP original se quitó de la raíz el 2026-11-03 (ya corregido); queda en `e337710` / tag `tp-cap1a4-entregado`.
- Copias creadas en C-01 con `git -c core.autocrlf=false archive e337710` (62 archivos c/u, verificadas idénticas al commit; tag local `tp-cap1a4-entregado`). `.gitattributes` (`parcial/** -text`, `despliegue/** -text`) evita que git altere sus finales de línea.
- Entrega: `.zip` con `parcial/` + `despliegue/` (ver [knowledge-base/12](knowledge-base/12_entregables_del_parcial.md)).

---

## Stack Tecnológico

| Capa | Tecnología | Versión mín. |
|------|------------|--------------|
| Lenguaje | Python | 3.12 |
| Web | FastAPI (handlers `async def`) | 0.111 |
| Modelos | SQLModel | 0.0.24 |
| ORM/Motor | SQLAlchemy asincrónico | 2.0 |
| Driver | asyncpg | 0.30 |
| BD | PostgreSQL | 16 |
| Migraciones | Alembic (plantilla async) | 1.13 |
| Config | pydantic-settings | 2.0 |
| Hash | bcrypt | 4.0 |
| Token | PyJWT | 2.8 |
| Servidor | uvicorn (`fastapi[standard]`) | — |
| Contenedor | Docker (base `python:3.12-alpine`) | 20.10 |
| Pruebas | `.http` (REST Client) + `solo_agregado.sql`, sin pytest (DD-01) | — |

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/` (índice en [README.md](knowledge-base/README.md)). **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Propósito y alcance |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Tablas, índices, migraciones, seed |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas RN-01..RN-16 |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Endpoints e historias por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura, env vars |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones DD-xx y supuestos |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | Inconsistencias a resolver ANTES de codear |
| [11_brecha_tp_vs_parcial.md](knowledge-base/11_brecha_tp_vs_parcial.md) | Qué cambiar respecto del TP |
| [12_entregables_del_parcial.md](knowledge-base/12_entregables_del_parcial.md) | Puntos, zip, Dockerfile, casos C y D |
| [13_auditoria_vs_pdf.md](knowledge-base/13_auditoria_vs_pdf.md) | Matriz de requisitos del PDF |

> ⚠️ Preguntas de prioridad **Alta** abiertas en `10_preguntas_abiertas.md`:
> - **Q-01**: nombre del grupo (el zip es `Parcial_Cap1a6_<NombreDelGrupo>.zip`).
> - **Q-02**: datos del VPS (host, usuario, puerto, URL pública, base de la cátedra) — **bloquea C-11**.
> - **Q-04**: nombres exactos de las variables de `Settings` (clave de firma, duración del token, costo bcrypt, cookie `Secure`, pool).
> - Q-03 (ubicación de `main.py`) ya está resuelta: `parcial/main.py` en la raíz (DD-08).

---

## Skills Disponibles

Instaladas a nivel proyecto (`.claude/skills/`, nunca `-g`). Fuente de verdad: `.atl/skill-registry.md`.

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | FastAPI / capas / lifespan / async | `fastapi`, `async-python-patterns` |
| **Datos** | Modelos, migraciones Alembic, esquema PG16 | `sqlalchemy-alembic-expert-best-practices-code-review`, `postgresql-table-design` |
| **Seguridad** | JWT, cookie, RBAC, bcrypt | `auth-implementation-patterns`, `async-python-patterns` |
| **Despliegue** | Dockerfile, imagen, VPS (`despliegue/`) | `multi-stage-dockerfile` |
| **Orquestación** | OPSX / KB / roadmap | `kb-creator`, `roadmap-generator`, `agent-instruction`, `skill-registry` (globales) |

Cargá la skill correspondiente al contexto ANTES de escribir código. `tdd` y `python-testing-patterns` siguen instaladas pero **no se usan** (sin pytest, DD-01).

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 12 changes (C-01..C-12), agrupados por ejercicio del PDF; sólo lo que piden las consignas.
- **Orden del parcial**: `C-01..C-04 (hechos) → C-05 autenticacion → C-06 autorizacion-roles-eventos → C-07 libros-clientes-ventas → C-08 lecturas-sin-n1 → C-09 seed-casos-readme`.
- **Rama de despliegue** (solo `despliegue/`, paralela tras C-01): `C-10 despliegue-imagen → C-11 despliegue-vps` (C-11 bloqueado por Q-02).
- **Cierre**: `C-12 empaquetado-zip` (tras C-09 y C-11).
- **Próximo change**: `C-10 despliegue-imagen` (rama de despliegue; `C-11` bloqueado por Q-02, `C-12` tras C-11).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y sus archivos de "Leer antes".

---

## Reglas Duras (específicas del proyecto)

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, engram; el Strict TDD global **no aplica** acá: DD-01): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.

Son contrato; romperlas es un defecto. Formato `NUNCA X → hacer Y`:

1. **Capas estrictas**: NUNCA pasar `AsyncSession` a un servicio → el Router arma el UoW, el Service lo abre y aplica reglas, el Repository (`BaseRepository[T]`/`SoftDeleteRepository[T]`) accede a datos, el Model define la tabla; el router traduce los errores.
2. NUNCA renombrar ni quitar tablas/columnas indicadas en el PDF → solo se pueden agregar columnas.
3. NUNCA `float` para dinero → `NUMERIC`/`Decimal`; las fechas nuevas siempre `timestamptz`.
4. NUNCA `create_all` ni SQL suelto para el esquema → migraciones Alembic (0003 autogenerada y leída antes de aplicar, con los índices únicos parciales; 0004 a mano para el disparador de sólo agregado).
5. NUNCA devolver al cliente texto interno de la base ni terminar en 500 por entrada inválida → `IntegrityError` traducido a 409 con mensaje propio; validación en el contrato (422).
6. NUNCA defaults para la clave de firma JWT ni la contraseña de la base, ni versionar `.env` → `Settings` (pydantic-settings) sin defaults; `env.example` sin secretos.
7. Todos los handlers `async def`; bcrypt fuera del bucle (`asyncio.to_thread`); motor y fábrica de sesiones en el lifespan (`app.state`), nunca al importar.
8. NUNCA autorizar con los roles del token → consultar `asignacion_rol` vigente en la base en cada petición; distinguir siempre 401 de 403.
9. NUNCA poner código en la raíz ni modificar la lógica de `despliegue/` → el parcial se hace en `parcial/`; `despliegue/` solo recibe Docker/VPS.
10. Las pruebas son las que pide el PDF: `.http` en `parcial/test/` (casos C con respuesta esperada en comentario) y `solo_agregado.sql`; sin pytest.
11. NUNCA commitear ni pushear sin pedido explícito → Conventional Commits en español.
12. Ante duda, el PDF manda sobre KB, plan y skills; si el PDF no lo resuelve → registrarlo en `knowledge-base/10_preguntas_abiertas.md`, no inventar.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. /opsx:apply (cargando skills)                 → verificar con los casos .http del PDF
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
