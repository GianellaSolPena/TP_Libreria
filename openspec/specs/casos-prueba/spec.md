# casos-prueba Specification

## Purpose
Definir los casos de prueba C-01..C-16 del parcial como archivos `.http` en `parcial/test/` (respuesta esperada en comentario, ejecutables tras `python seed.py`) y la evidencia asociada en `parcial/evidencia/`, ya que el proyecto no usa pytest (DD-01).

## Requirements

### Requirement: Un archivo por caso, reproducible tras el seed
`parcial/test/` SHALL contener un archivo `.http` por cada caso C-01..C-16 salvo C-14 (que es `solo_agregado.sql`), con el número del caso al comienzo del nombre. Cada archivo MUST poder correrse de principio a fin, en orden, inmediatamente después de `python seed.py` y con el servidor arriba, sin pasos manuales previos en la base y sin depender de otro archivo. Cada archivo MUST indicar al comienzo sus precondiciones (seed, servidor, `SQL_ECHO` si corresponde). Los ids y credenciales usados MUST ser los del seed o tomarse de respuestas anteriores del mismo archivo.

#### Scenario: Corrida completa
- **WHEN** para cada archivo de casos se corre `python seed.py` y luego todas sus peticiones en orden
- **THEN** cada petición responde con el código y el contenido esperados que indica su comentario

#### Scenario: Orden arbitrario entre archivos
- **WHEN** se corren los archivos en cualquier orden, con `python seed.py` antes de cada uno
- **THEN** los resultados son los mismos que en el orden numérico

### Requirement: Respuesta esperada documentada
Cada petición de los archivos de casos SHALL llevar en un comentario el código HTTP esperado y lo que debe verse en la respuesta (campos, encabezados o mensaje). Lo que sólo puede comprobarse en la base (filas sueltas, `intento_acceso`, `stock == SUM(movimientos)`, fila revocada) MUST quedar como consulta SQL comentada junto con su resultado esperado.

#### Scenario: Lectura del archivo
- **WHEN** se lee cualquier petición de un archivo de casos
- **THEN** inmediatamente antes o después hay un comentario con el código esperado y lo que se comprueba

### Requirement: Varias sesiones en un mismo archivo
Los casos que necesitan más de un usuario a la vez SHALL nombrar cada login con `# @name` y enviar sus peticiones con `# @no-cookie-jar` y el encabezado `Cookie:` tomado del `Set-Cookie` de ese login, de modo que las sesiones no se mezclen. Las peticiones que deben ir sin sesión MUST llevar `# @no-cookie-jar` sin encabezado `Cookie`.

#### Scenario: Administrador y vendedor a la vez (C-07)
- **WHEN** en el archivo de C-07 el ADMIN revoca el rol del vendedor y luego el vendedor repite una petición con su misma cookie
- **THEN** cada petición viaja con la cookie de su propio login y la del vendedor recibe 403

### Requirement: Cobertura de los casos C del PDF
Los archivos SHALL demostrar, sobre los datos iniciales, el resultado esperado que el PDF fija para cada caso:
- C-01: parámetro de ruta no entero con sesión iniciada → 422.
- C-02: registro 201; correo repetido de un usuario y correo de un cliente existente → 409 con mensaje propio, sin filas sueltas.
- C-03: `Set-Cookie` con HttpOnly, SameSite=Lax y Max-Age; cuerpo sin token; sin cookie o sólo con `Authorization: Bearer` → 401.
- C-04: correo existente con contraseña mala y correo inexistente → 401 con el mismo cuerpo.
- C-05: seis intentos fallidos seguidos → el sexto 429 con `Retry-After`; los cinco fallos en `intento_acceso`.
- C-06: sin sesión 401; el vendedor que crea un libro 403; la cliente ve su venta 200 y la ajena 403.
- C-07: revocar un rol con la sesión abierta → la misma cookie recibe 403 en la petición siguiente, `/auth/yo` muestra la diferencia entre roles del token y vigentes, la fila revocada sigue; vencimiento pasado o sin zona → 422.
- C-08: el ADMIN no puede revocarse su propio ADMIN → 409.
- C-09: con el cambio obligatorio pendiente, 403 salvo `/auth`; tras el cambio, `debe_cambiar_password` falso y la misma cookie entra a una ruta protegida (200).
- C-10: venta válida de dos renglones → 201 con precios copiados y total; stock baja; un movimiento por renglón; aviso en el log después de la respuesta.
- C-11: venta con Rayuela ×1 y Bestiario ×2 → 409; sin venta nueva, sin descuentos ni movimientos; Rayuela sigue en 10.
- C-12: venta con cliente inexistente, con libro inexistente y con libro dado de baja → 409 en los tres, sin escrituras.
- C-13: reponer → 200 con su movimiento; baja → 204 y deja de aparecer en el catálogo; alta con el mismo ISBN → 201; un segundo vigente con ese ISBN → 409; la venta vieja sigue mostrando el título.
- C-15: detalle de una venta de 2 renglones y de una de 4 → misma cantidad de consultas.
- C-16: búsqueda `' OR '1'='1` → lista vacía con `total` 0; `titulo=ficc&size=1` → `total` 1, `pages` 1, y `page=2` → 422; `size=500` → 422; PATCH parcial cambia sólo lo enviado; PATCH con `stock` → 422.

#### Scenario: La cliente ve lo propio (C-06)
- **WHEN** en el archivo de C-06 el vendedor registra una venta para Ana Paz y luego `ana@example.com` pide esa venta y la venta 1
- **THEN** la propia responde 200 y la venta 1 de Lucía responde 403

#### Scenario: Venta sin stock suficiente (C-11)
- **WHEN** en el archivo de C-11 el vendedor intenta la venta y luego se consulta Rayuela y los movimientos
- **THEN** la venta responde 409, `GET /libros/1` muestra stock 10 y la consulta comentada muestra `stock == SUM(movimientos)` en los cinco libros

#### Scenario: Título en la venta vieja (C-13)
- **WHEN** en el archivo de C-13 se da de baja Ficciones (vendida en la venta 1) y se pide `GET /ventas/1`
- **THEN** responde 200 y el renglón muestra el título «Ficciones»

#### Scenario: Cambio obligatorio con el usuario del seed (C-09)
- **WHEN** en el archivo de C-09 `nuevo@example.com` inicia sesión, pide una ruta protegida, cambia su contraseña y repite la ruta con la misma cookie
- **THEN** la primera responde 403, el cambio 200 y la repetición 200

### Requirement: Archivos de pruebas obsoletos retirados
`parcial/test/` MUST NOT contener `seed.sql`, los `.http` del TP con su numeración anterior (incluido `C-07_consultas_fijas.http`), capturas del TP ni archivos `.http` que dependan de usuarios o datos creados a mano por psql. Sólo MUST quedar los archivos de casos C-01..C-16 y `solo_agregado.sql`.

#### Scenario: Contenido de la carpeta
- **WHEN** se lista `parcial/test/`
- **THEN** hay quince archivos `.http` cuyos nombres empiezan con C-01..C-13, C-15 y C-16, y `solo_agregado.sql`, y nada más

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

### Requirement: Caso extra de RN-15 con carácter nulo
`parcial/test/` SHALL incluir un archivo `.http` extra (no es un caso C del PDF, no lleva número C) que demuestre RN-15 con textos que contienen U+0000, con las mismas convenciones que los demás archivos: precondiciones al comienzo, ejecutable tras `python seed.py`, `# @no-cookie-jar` y `Cookie:` por sesión, y la respuesta esperada en un comentario junto a cada petición. MUST cubrir al menos la búsqueda `GET /libros?titulo=a%00b`, el login con U+0000 en el correo y un alta con sesión de ADMIN con U+0000 en un texto, todos con 422, y una petición de control válida que siga respondiendo como antes.

#### Scenario: Corrida del caso extra
- **WHEN** tras `python seed.py` y con el servidor arriba se corren en orden todas las peticiones del archivo
- **THEN** cada una responde con el código del comentario: 422 para las entradas con U+0000 y el código habitual para la petición de control, y ninguna responde 500

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
