# Spec Delta

## MODIFIED Requirements

### Requirement: Evidencia de los casos C-14 y C-15
`parcial/evidencia/` SHALL contener la salida de psql de `test/solo_agregado.sql` (C-14), con los dos rechazos del disparador, y la captura cruda de la consola de uvicorn con `SQL_ECHO=true` de los detalles de la venta de 2 renglones y de la de 4 (C-15), ambas tomadas sobre una base PostgreSQL 16 cargada con `python seed.py`. La captura de C-15 MUST ser la salida de consola sin recortes ni líneas truncadas (sentencias completas, líneas de parámetros y las líneas `INFO: ... HTTP/1.1` que separan las peticiones); el conteo de SELECT por petición MAY agregarse como anotación al final, separado de la captura. Si `parcial/evidencia/` contiene una imagen de la corrida de C-14, MUST mostrar los mismos conteos de movimientos que el archivo de texto. Cada archivo de texto MUST indicar al comienzo cómo se obtuvo (comandos, versión de PostgreSQL y fecha).

#### Scenario: Revisión de la evidencia
- **WHEN** se revisa `parcial/evidencia/`
- **THEN** hay un archivo de C-14 con los errores «UPDATE no permitido» y «DELETE no permitido», y uno de C-15 con la misma cantidad de SELECT para 2 y para 4 renglones, sin referencias a datos de prueba de changes anteriores

#### Scenario: Captura cruda de C-15
- **WHEN** se lee el archivo de C-15
- **THEN** ninguna línea de la captura termina en `[...]` ni fue resumida, y entre las dos líneas `GET /ventas/... HTTP/1.1` de los detalles aparecen todas las sentencias que emitió cada petición

#### Scenario: Texto e imagen de C-14 coherentes
- **WHEN** se comparan `C-14_solo_agregado.txt` y la imagen de C-14
- **THEN** ambos muestran 7 movimientos antes y 7 después, y los mismos dos errores del disparador

## ADDED Requirements

### Requirement: Evidencia de corrida de los casos que escriben datos
`parcial/evidencia/` SHALL contener un archivo de corrida por cada caso cuyos `.http` escriben datos: C-02, C-05, C-07, C-08, C-10, C-11, C-12, C-13 y C-16. Cada archivo MUST indicar al comienzo cómo se obtuvo y MUST registrar, por cada petición del `.http` en orden, el comentario esperado, la respuesta real y si coincide; las consultas psql comentadas MUST figurar con su salida real.

#### Scenario: Corrida que coincide
- **WHEN** se lee el archivo de corrida de cualquiera de esos casos
- **THEN** cada petición del `.http` aparece con su respuesta real y figura como coincidente con su comentario, y las consultas psql muestran el resultado esperado (por ejemplo `stock == SUM(movimientos)` en C-10, C-11 y C-12)

#### Scenario: Aviso del comprobante en C-10
- **WHEN** se lee el archivo de corrida de C-10
- **THEN** incluye el fragmento de consola de uvicorn donde la línea «Comprobante de la venta N enviado al cliente» aparece después de la línea `POST /ventas HTTP/1.1" 201`, con N igual al id de la venta creada

### Requirement: Corridas sobre una base descartable
Las corridas que producen la evidencia de `parcial/evidencia/` SHALL hacerse sobre una base PostgreSQL 16 descartable, con `python seed.py` inmediatamente antes de cada archivo de casos, y MUST NOT hacerse contra la base local del usuario. El encabezado de cada archivo MUST declarar la base usada, los comandos, la fecha y las versiones de PostgreSQL y de Python.

#### Scenario: Encabezado de una corrida
- **WHEN** se lee el encabezado de cualquier archivo de corrida
- **THEN** declara una base descartable PostgreSQL 16, el `seed.py` previo, los comandos usados y la fecha

### Requirement: Evidencia sin secretos
Ningún archivo de `parcial/evidencia/` SHALL contener contraseñas de base de datos ni claves de firma de tokens. Los valores de token de sesión de las respuestas MAY reemplazarse por una marca fija, indicándolo en el encabezado del archivo.

#### Scenario: Sin secretos
- **WHEN** se buscan en `parcial/evidencia/` la contraseña del contenedor descartable y la clave de firma usadas en la corrida
- **THEN** no aparecen en ningún archivo
