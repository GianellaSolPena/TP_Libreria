## MODIFIED Requirements

### Requirement: Guía de los casos de prueba y la evidencia
`parcial/README.md` SHALL listar los usuarios del seed con su rol y su contraseña de mentira, explicar que antes de cada archivo de casos se corre `python seed.py`, indicar la extensión con la que se corren los `.http` y cómo se manejan varias sesiones, y traer una tabla con cada caso C-01..C-16, su archivo y qué demuestra. La tabla SHALL incluir también los casos extra que no son del PDF (por ejemplo `RN-15_caracter_nulo.http`), marcados como extra. MUST indicar qué casos requieren `SQL_ECHO=true` o psql, y MUST nombrar cada archivo de `parcial/evidencia/` junto al caso o la verificación que respalda (C-14, C-15 y la evidencia reproducible de migraciones y casos que se agregue), sin referencias a archivos que no existan.

#### Scenario: Ubicar un caso
- **WHEN** se busca en el README el caso C-14 o C-15
- **THEN** la tabla indica el archivo que lo demuestra, la condición para correrlo y el archivo de `evidencia/` correspondiente

#### Scenario: Caso extra de RN-15
- **WHEN** se busca en el README `RN-15_caracter_nulo.http`
- **THEN** aparece en la tabla de casos, marcado como extra, con qué demuestra (U+0000 en la entrada → 422, nunca 500)

#### Scenario: README coherente con las carpetas
- **WHEN** se comparan los archivos de `parcial/test/` y `parcial/evidencia/` con los que nombra el README
- **THEN** cada archivo de esas carpetas está mencionado y cada archivo mencionado existe
