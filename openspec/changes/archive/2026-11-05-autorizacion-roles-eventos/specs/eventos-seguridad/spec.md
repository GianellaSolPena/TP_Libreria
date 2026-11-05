# Spec Delta

## Purpose

Deja en `evento_seguridad` una línea por cada alta de personal, cambio de rol y cambio de contraseña, en la misma transacción que el cambio (RN-16), registra los datos iniciales con el actor textual `SISTEMA` y permite al administrador consultar ese historial paginado.

## ADDED Requirements

### Requirement: Evento en la misma transacción
Cada alta de personal, asignación de rol y revocación de rol SHALL dejar exactamente una línea en `evento_seguridad` con `cuando`, `actor` (el correo de quien hizo el cambio) y `accion` (texto que nombra la operación, el usuario afectado y el rol), escrita en la misma transacción que el cambio: si el cambio se rechaza, el evento MUST NOT quedar, y no MUST quedar un cambio sin su evento. El cambio de contraseña conserva el evento que ya exige `autenticacion`.

#### Scenario: Asignación con evento
- **WHEN** un ADMIN asigna VENDEDOR a un usuario con éxito
- **THEN** existe una línea nueva en `evento_seguridad` con el correo del ADMIN como `actor` y una `accion` que nombra la asignación, el usuario y el rol

#### Scenario: Revocación rechazada sin evento
- **WHEN** un ADMIN intenta revocarse su propio ADMIN y recibe 409
- **THEN** no se agregó ninguna línea a `evento_seguridad`

#### Scenario: Alta de personal rechazada sin evento
- **WHEN** `POST /usuarios` responde 409 por correo repetido
- **THEN** no se agregó ninguna línea a `evento_seguridad`

### Requirement: Actor SISTEMA para los datos iniciales
Los eventos de la carga de datos iniciales SHALL registrarse con `actor = "SISTEMA"`, un texto que no corresponde a ningún usuario.

#### Scenario: Evento de la carga inicial
- **WHEN** se cargan los datos iniciales
- **THEN** `evento_seguridad` tiene una línea con `actor` `SISTEMA` y `accion` «Carga de los datos iniciales»

### Requirement: Consulta del historial de seguridad
`GET /eventos` (sólo ADMIN) SHALL responder 200 con el envoltorio de paginación (`items`, `total`, `page`, `size`, `pages`) de las líneas de `evento_seguridad`, de la más reciente a la más antigua, aceptando `page` y `size` con los límites comunes de los listados (422 fuera de rango o página inexistente).

#### Scenario: Primera página
- **WHEN** un ADMIN pide `GET /eventos?size=2`
- **THEN** responde 200 con las dos líneas más recientes y `total` igual a la cantidad de líneas guardadas

#### Scenario: Tamaño fuera de rango
- **WHEN** se pide `GET /eventos?size=0`
- **THEN** responde 422
