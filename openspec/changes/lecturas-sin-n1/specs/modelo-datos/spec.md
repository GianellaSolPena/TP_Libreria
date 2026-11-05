# Spec Delta

## MODIFIED Requirements

### Requirement: Navegación en los dos extremos
Cada relación nueva SHALL declararse en ambos modelos: `Usuario`↔`AsignacionRol`, `Usuario`↔`Cliente` (objeto en los dos lados), `Usuario`↔`MovimientoStock`, `Libro`↔`MovimientoStock` y `Venta`↔`MovimientoStock`. Recorrer cualquiera de los dos extremos MUST requerir que ese extremo se haya cargado de antemano en la misma lectura; ningún extremo MUST cargarse en forma diferida al accederlo.

#### Scenario: Navegación recíproca
- **WHEN** se carga un movimiento con su libro, su usuario y su venta, precargando también la colección de movimientos de cada uno, y desde cada uno se recorre esa colección
- **THEN** el movimiento original aparece en `Libro.movimientos`, `Usuario.movimientos` y `Venta.movimientos`

#### Scenario: Extremo no precargado
- **WHEN** se carga un libro sin precargar su colección de movimientos y se intenta recorrerla
- **THEN** no se emite una consulta diferida y la lectura falla de forma explícita
