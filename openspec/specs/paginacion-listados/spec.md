# paginacion-listados Specification

## Purpose

Define la forma común de todos los listados de la API: el envoltorio `{items, total, page, size, pages}` y los límites de sus parámetros (PDF Ej. 3, sección 2.9).

## Requirements

### Requirement: Envoltorio de listados
Todo listado SHALL responder `{items, total, page, size, pages}`, donde `total` cuenta las filas con los mismos filtros que la página y `pages` es la cantidad de páginas de tamaño `size` necesarias para `total`, con un mínimo de una.

#### Scenario: Listado con resultados
- **WHEN** hay 5 elementos y se pide `page=1&size=2`
- **THEN** responde 200 con 2 `items`, `total` 5, `page` 1, `size` 2 y `pages` 3

#### Scenario: Cero resultados
- **WHEN** no hay elementos y se pide el listado sin parámetros
- **THEN** responde 200 con `items` vacío, `total` 0, `page` 1, `size` 20 y `pages` 1

### Requirement: Parámetros de paginación acotados
`page` SHALL empezar en 1 (por defecto 1) y `size` SHALL ir de 1 a 100 (por defecto 20); un valor fuera de rango o no entero MUST responder 422 sin consultar la base.

#### Scenario: Tamaño fuera de rango
- **WHEN** se pide `size=500` o `size=0`
- **THEN** responde 422

#### Scenario: Página cero
- **WHEN** se pide `page=0`
- **THEN** responde 422

### Requirement: Página inexistente
Pedir una página posterior a la última SHALL responder 422 con el mensaje «La página N no existe: hay M».

#### Scenario: Página de más
- **WHEN** hay 3 páginas y se pide `page=4`
- **THEN** responde 422 con el mensaje «La página 4 no existe: hay 3»

#### Scenario: Página de más sin resultados
- **WHEN** no hay elementos y se pide `page=2`
- **THEN** responde 422 con el mensaje «La página 2 no existe: hay 1»
