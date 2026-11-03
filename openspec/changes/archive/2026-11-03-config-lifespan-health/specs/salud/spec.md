## Purpose

Expone el estado del proceso a quien lo supervisa (un HEALTHCHECK, un balanceador o una persona) distinguiendo un proceso vivo de uno listo para atender, porque reiniciar el proceso no arregla una base caída.

## ADDED Requirements

### Requirement: Proceso vivo sin tocar la base
`GET /health/live` SHALL responder 200 sin autenticación y MUST NOT consultar la base de datos.

#### Scenario: Vivo con la base disponible
- **WHEN** se pide `GET /health/live` con la base disponible
- **THEN** responde 200

#### Scenario: Vivo con la base caída
- **WHEN** la base está detenida y se pide `GET /health/live`
- **THEN** responde 200

### Requirement: Proceso listo según la base
`GET /health/ready` SHALL responder sin autenticación ejecutando `SELECT 1` contra la base: 200 si contesta y 503 si no contesta, sin exponer texto interno de la base.

#### Scenario: Listo con la base disponible
- **WHEN** se pide `GET /health/ready` con la base disponible
- **THEN** responde 200

#### Scenario: No listo con la base caída
- **WHEN** la base está detenida y se pide `GET /health/ready`
- **THEN** responde 503 con un cuerpo propio de la aplicación, sin texto del driver ni de PostgreSQL, y nunca 500

#### Scenario: Se recupera sin reiniciar
- **WHEN** la base vuelve a estar disponible después de un 503 y se pide `GET /health/ready` otra vez
- **THEN** responde 200 sin haber reiniciado el proceso
