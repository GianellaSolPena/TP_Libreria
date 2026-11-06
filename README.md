# Librería · Parcial Programación III (Capítulos 1-6)

Integrantes: Agustina Fontagnol, Martina Suarez, Gianella Peña y Yoselie Aquino

API REST con FastAPI, SQLModel y PostgreSQL (asyncpg). El repo tiene dos proyectos independientes,
cada uno con su propio `app/`, `migrations/`, `alembic.ini`, `requirements.txt`, `env.example` y `test/`:

| Carpeta | Qué es |
|---|---|
| `parcial/` | El TP Cap 1-4 evolucionado con lo que pide el parcial (consigna: `Parcial_Cap1a6_Consigna.pdf`). Se corre desde `parcial/` con `uvicorn main:app`. Ver [parcial/README.md](parcial/README.md). |
| `despliegue/` | Copia congelada del TP Cap 1-4 más el Dockerfile, para la imagen y el VPS (ejercicios 9-10). Ver [despliegue/README.md](despliegue/README.md). |

El TP Cap 1-4 tal como se entregó (nota 10) queda en el historial de git: commit `e337710`, tag
`tp-cap1a4-entregado`.

## Planificación

- `knowledge-base/` — base de conocimiento del dominio.
- `CHANGES.md` — secuencia de changes del parcial.
- `openspec/` — specs y changes (flujo OPSX).
