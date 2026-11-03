# Visión y Objetivos

> Fuente de autoridad: `Parcial_Cap1a6_Consigna.pdf` (Programación III, TUP, UTN-FRM; "Unidades 1 a 6 — Del objeto a la transacción", 24 páginas). Todo lo que sigue deriva de ese PDF y del código ya entregado del TP Cap 1-4. No existe carpeta `docs/`.

## Propósito del sistema
API REST asincrónica de una **librería** (catálogo, clientes, ventas) que el parcial lleva del TP de los capítulos 1-4 hasta el capítulo 6: se le agregan **acceso con usuarios y roles** (cap. 5), una **capa de repositorios con Unit of Work** que agrupa las escrituras de cada operación (cap. 6) y, **aparte**, el **despliegue en un VPS dentro de un contenedor Docker del TP Cap 1-4 tal como se entregó**.

El parcial se resuelve **agregando modificaciones sobre el código existente**, no reescribiendo desde cero (ver `11_brecha_tp_vs_parcial.md`).

## Qué debe demostrar el grupo (objetivos del PDF)
1. Reorganizar la API asincrónica en capas **Router → Service → UoW → Repository → Model**.
2. Evolucionar el esquema con Alembic: una migración **autogenerada y leída** antes de aplicarla, y otra **escrita a mano** (lo que el autogenerate no ve: funciones/disparadores).
3. Autenticar con **bcrypt** y **JWT en cookie HttpOnly**, sin frenar el servidor (bcrypt fuera del event loop) y sin revelar qué cuentas existen.
4. Autorizar consultando los **roles en la base en cada petición**, con vigencia, distinguiendo siempre **401 vs 403**.
5. Agrupar en **una sola transacción** las escrituras de cada operación de negocio.
6. Delegar en la base lo que la base garantiza: unicidad entre vigentes, FKs, CHECKs y el sólo-agregado.
7. Empaquetar el TP Cap 1-4 en una imagen Docker y ponerlo en línea en el VPS sin filtrar secretos.

## Objetivos por actor
| Actor | Objetivo principal | Secundarios |
|---|---|---|
| ADMIN | Mantener catálogo, reponer stock, administrar personal y roles | Ver historial de seguridad (`/eventos`) y movimientos de stock |
| VENDEDOR | Registrar ventas y atender clientes en el mostrador | Alta/edición de clientes y perfiles |
| CLIENTE | Auto-registrarse en la web y consultar sus compras (`/mis-ventas`) | Ver detalle de sus propias ventas |
| Anónimo | Ver el catálogo (público) y usar `/auth` | — |
| Corrector (cátedra) | Verificar casos C (parcial) y D (despliegue) | Revisar historial `.git` si va en el zip |

## Alcance (lo que SÍ hace)
- Módulos mínimos: `health`, `usuarios`, `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`.
- Auth: registro, login (cookie), logout, `/auth/yo`, cambio de contraseña (con cambio obligatorio).
- Roles ADMIN/VENDEDOR/CLIENTE en tabla propia con vigencia; revocación sin borrar la fila.
- Stock sólo vía `movimiento_stock` (alta, reposición, venta); disparador sólo-agregado.
- Borrado lógico de libros con ISBN único entre vigentes.
- Listados con envoltorio `{items,total,page,size,pages}`.
- Aviso de comprobante con `BackgroundTasks` (simulado).
- Despliegue del TP Cap 1-4 en VPS (Ejercicios 9 y 10, carpeta aparte).

## Fuera de alcance (explícito en el PDF)
- **Concurrencia (cap. 7)**: no se evalúa; el lost-update de dos ventas simultáneas del último ejemplar se acepta (el CHECK `stock >= 0` no lo detecta porque ambas escriben 0).
- **Colas con Redis (cap. 8)**: el aviso es `BackgroundTasks` en el mismo proceso; si reinicia, se pierde.
- Segundo mecanismo de sólo-agregado por permisos del rol de base (sec. 6.9): no se pide (un solo rol de base); tener ambos sería defensa en profundidad.
- **Docker Compose**: no se usa; la base no forma parte del paquete.
- Invalidar sesiones o emitir token nuevo al cambiar la contraseña: no se hace (login tradicional con cookie).
- Las demás modificaciones del parcial **no** van en el despliegue (el VPS corre el TP Cap 1-4 congelado).

## Métricas de éxito
Total 100 puntos en 10 ejercicios (ver `12_entregables_del_parcial.md`). Regla dura: un proyecto que no levanta, que no crea su esquema con `alembic upgrade head` sobre base vacía, o que contiene credenciales reales en el repositorio, la imagen o el zip **no se corrige hasta que se subsane**.
