## ADDED Requirements

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
`parcial/evidencia/` SHALL contener la salida de psql de `test/solo_agregado.sql` (C-14), con los dos rechazos del disparador, y el fragmento de consola con `SQL_ECHO=true` de los detalles de la venta de 2 renglones y de la de 4 (C-15), ambos tomados sobre una base cargada con `python seed.py`. Cada archivo MUST indicar al comienzo cómo se obtuvo (comando y fecha).

#### Scenario: Revisión de la evidencia
- **WHEN** se revisa `parcial/evidencia/`
- **THEN** hay un archivo de C-14 con los errores «UPDATE no permitido» y «DELETE no permitido», y uno de C-15 con la misma cantidad de SELECT para 2 y para 4 renglones, sin referencias a datos de prueba de changes anteriores
