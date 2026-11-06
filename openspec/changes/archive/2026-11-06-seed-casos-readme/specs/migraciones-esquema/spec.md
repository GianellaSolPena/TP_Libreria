## MODIFIED Requirements

### Requirement: Script de demostración del caso C-14
`parcial/test/solo_agregado.sql` SHALL demostrar en psql que UPDATE y DELETE sobre `movimiento_stock` son rechazados por el disparador, funcionando tanto sobre una base recién migrada como sobre una con datos iniciales, y sin dejar filas nuevas al terminar. La salida de una corrida sobre la base cargada con `python seed.py` MUST guardarse en `parcial/evidencia/` como captura del caso C-14.

#### Scenario: Ejecución del script
- **WHEN** se ejecuta `psql -f test/solo_agregado.sql` contra la base en head
- **THEN** la salida muestra un error del disparador para el UPDATE y otro para el DELETE, y al terminar la base tiene las mismas filas que antes

#### Scenario: Captura entregable
- **WHEN** se revisa `parcial/evidencia/` después de correr el script sobre los datos iniciales
- **THEN** hay un archivo con la salida de psql que muestra los dos rechazos y que el conteo de movimientos antes y después es 7
