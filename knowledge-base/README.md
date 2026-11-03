# Librería (Parcial Cap 1-6) — Base de Conocimiento

Base de conocimiento generada (Mode A, ingest silencioso) a partir de `Parcial_Cap1a6_Consigna.pdf` (autoridad) y del código ya entregado del TP Cap 1-4. No hay carpeta `docs/`; el PDF no se movió ni copió.

## Índice de archivos
| Archivo | Contenido |
|---|---|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, objetivos del parcial, alcance, fuera de alcance |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack, arquitectura en capas, dos proyectos, requisitos no funcionales |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, matriz RBAC, rutas públicas, usuarios del seed |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Tablas y columnas obligatorias, índices parciales, migraciones, seed |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | RN-01..RN-16 con su garante + reglas derivadas de cada ejercicio |
| [06_funcionalidades.md](06_funcionalidades.md) | Endpoints de referencia por épica y historias clave |
| [07_flujos_principales.md](07_flujos_principales.md) | Registro, login, autorización, roles, venta, libro, despliegue |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones, estructura de directorios obligatoria, seguridad, variables de entorno |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones (incl. strict TDD con pytest) y supuestos |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Inconsistencias y preguntas priorizadas (grupo, VPS, etc.) |
| [11_brecha_tp_vs_parcial.md](11_brecha_tp_vs_parcial.md) | Estado actual del código vs. requerido, por área |
| [12_entregables_del_parcial.md](12_entregables_del_parcial.md) | Puntos por ejercicio, contenido del zip, Dockerfile, casos C y D |
| [13_auditoria_vs_pdf.md](13_auditoria_vs_pdf.md) | Matriz de requisitos del PDF (con página) vs. KB y CHANGES.md, antes/después de la auditoría |

## Quick Start
1. Dominio y alcance -> [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Datos -> [04](04_modelo_de_datos.md); reglas -> [05](05_reglas_de_negocio.md)
3. Qué hay que cambiar en el código -> [11](11_brecha_tp_vs_parcial.md)
4. Arquitectura -> [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar -> [06](06_funcionalidades.md), [07](07_flujos_principales.md)
6. Entrega y puntos -> [12](12_entregables_del_parcial.md)
7. Antes de codificar -> [10](10_preguntas_abiertas.md)

## Resumen ejecutivo
API FastAPI + SQLModel + PostgreSQL 16 (asyncpg) de una librería. El parcial agrega sobre el TP Cap 1-4 autenticación (bcrypt + JWT en cookie HttpOnly), autorización por roles vigentes en base, repositorios + Unit of Work, stock por movimientos con disparador de sólo agregado y borrado lógico de libros. Además se despliega, aparte, el TP Cap 1-4 congelado en Docker (base `python:3.12-alpine`) en el VPS de la cátedra. 100 puntos en 10 ejercicios; implementación con strict TDD (pytest) por decisión del grupo.
