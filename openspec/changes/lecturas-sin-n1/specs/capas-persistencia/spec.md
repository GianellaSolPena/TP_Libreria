# Spec Delta

## MODIFIED Requirements

### Requirement: Reparto de responsabilidades por capa
El router SHALL construir el Unit of Work con una dependencia y pasarlo al servicio sin abrirlo; el servicio SHALL abrirlo con `async with` y aplicar las reglas; el servicio MUST NOT recibir ni usar la sesión, construir su Unit of Work, confirmar ni revertir. El router MUST NOT usar la sesión para otra cosa que construir el Unit of Work en esa dependencia, ni confirmar ni revertir. Esto MUST cumplirse en todos los módulos, con la única excepción del registro de intentos de acceso.

#### Scenario: Revisión de servicios migrados
- **WHEN** se buscan referencias a la sesión, `commit(` o `rollback(` en los servicios de todos los módulos
- **THEN** no aparece ninguna

#### Scenario: Revisión de routers
- **WHEN** se buscan referencias a la sesión, `commit(` o `rollback(` en los routers de todos los módulos
- **THEN** la sesión sólo aparece como parámetro de la dependencia que construye el Unit of Work del módulo (y la fábrica de sesiones sólo en la del registro de intentos de acceso documentado), y no aparece ningún `commit(` ni `rollback(`
