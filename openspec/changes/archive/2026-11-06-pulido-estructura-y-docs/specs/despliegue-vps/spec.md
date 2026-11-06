## MODIFIED Requirements

### Requirement: DEPLOY.md completo
`despliegue/DEPLOY.md` SHALL incluir la URL pública, el día y la hora del despliegue, que la imagen se construyó en el servidor y cómo se llevaron los archivos, los comandos `docker build` y `docker run` completos tal como se ejecutaron (con el nombre del archivo de variables y sin su contenido), la base y la red usadas, el comando de datos iniciales, los cambios hechos al TP para que corra en el contenedor, y cómo se actualiza (reconstruir, `docker rm -f libreria`, mismo `docker run`; los datos viven en la base). Los comandos que no entran cómodos en una línea (más de ~100 caracteres) SHALL partirse en varias líneas con `\` al final, sin cambiar ningún argumento, de modo que el bloque se pueda copiar y pegar tal cual en un shell POSIX.

#### Scenario: Comandos reproducibles
- **WHEN** se ejecutan en el servidor, en orden, los comandos de actualización de `DEPLOY.md`
- **THEN** el contenedor vuelve a `healthy` en la misma URL con los mismos datos

#### Scenario: Sin pendientes
- **WHEN** se lee `DEPLOY.md` al cerrar el change
- **THEN** no quedan marcas de "pendiente" en URL, fecha y hora, lugar de construcción ni casos D-03/D-08

#### Scenario: Comandos largos partidos
- **WHEN** se buscan en los bloques de código de `DEPLOY.md` líneas de comando de más de ~100 caracteres
- **THEN** no hay ninguna, y al unir las líneas terminadas en `\` se obtienen exactamente los mismos argumentos que antes del cambio
