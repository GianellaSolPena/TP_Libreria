# ventas Specification

## Purpose
Registra ventas que nacen con sus renglones y descuentan el stock en una sola transacción, y permite consultarlas al personal y a cada cliente sólo las propias, con el aviso del comprobante en segundo plano (PDF Ej. 5, 6 y 8; RN-09, RN-10, RN-13, RN-14).

## Requirements

### Requirement: Contrato de la venta
`POST /ventas` (VENDEDOR, ADMIN) SHALL recibir sólo `cliente_id` y `renglones` (al menos uno), cada renglón con `libro_id` y `cantidad` entera >= 1. El contrato MUST rechazar con 422 los campos no declarados (incluidos `precio`, `precio_unitario`, `total` y `fecha`), `renglones` vacío, un `libro_id` repetido y `cantidad` < 1 o fuera del rango de un entero de 32 bits. Las ventas MUST NOT poder modificarse: no existe `PATCH` ni `DELETE` de ventas.

#### Scenario: Precio en el cuerpo
- **WHEN** el personal envía `POST /ventas` con `precio_unitario` en un renglón
- **THEN** responde 422 y no queda ninguna escritura

#### Scenario: Libro repetido
- **WHEN** el personal envía dos renglones con el mismo `libro_id`
- **THEN** responde 422

#### Scenario: Sin renglones
- **WHEN** el personal envía `{"cliente_id": 1, "renglones": []}`
- **THEN** responde 422

### Requirement: Registro de la venta en una sola transacción
Una venta válida SHALL crear, en una sola transacción, la venta con la fecha del servidor, sus renglones con el `precio_unitario` copiado del precio vigente de cada libro, el `total` calculado por el servidor como la suma de cantidad por precio unitario, el descuento del stock de cada libro y un movimiento de stock por renglón con cantidad negativa igual a la del renglón, motivo «Venta», el `venta_id` de la venta y el usuario que la registró. Responde 201 con el detalle de la venta (cliente, renglones con título, cantidad, precio unitario y subtotal, y total).

#### Scenario: Venta válida con dos renglones
- **WHEN** el personal registra una venta con 2 ejemplares del libro 1 (precio 25000.00, stock 10) y 1 del libro 4 (precio 27000.00, stock 3)
- **THEN** responde 201 con precios unitarios 25000.00 y 27000.00 y total 77000.00; el stock queda en 8 y 2; hay dos movimientos nuevos (-2 y -1) con el `venta_id` y el `usuario_id` del vendedor; y para cada libro `stock` coincide con la suma de sus movimientos

### Requirement: Venta rechazada sin escrituras
Si algún libro no tiene stock suficiente, si el cliente no existe, si algún libro no existe o si algún libro está dado de baja, la venta SHALL responder 409 con un mensaje propio y no MUST quedar ninguna de sus escrituras: ni la venta, ni los renglones, ni los descuentos, ni los movimientos, aunque otros renglones sí fueran válidos.

#### Scenario: Un libro alcanza y otro no
- **WHEN** el personal registra una venta con 1 Rayuela (stock 10) y 2 Bestiario (stock 1)
- **THEN** responde 409; no hay venta nueva, ni renglones, ni movimientos; Rayuela sigue en 10 y Bestiario en 1; y la suma de movimientos coincide con el stock en todos los libros

#### Scenario: Cliente inexistente
- **WHEN** el personal registra una venta con un `cliente_id` que no existe
- **THEN** responde 409 sin escrituras

#### Scenario: Libro inexistente
- **WHEN** el personal registra una venta con un `libro_id` que no existe
- **THEN** responde 409 sin escrituras

#### Scenario: Libro dado de baja
- **WHEN** el personal registra una venta con un libro dado de baja
- **THEN** responde 409 sin escrituras

### Requirement: Aviso del comprobante en segundo plano
Al confirmarse una venta, la aplicación SHALL agendar un aviso del comprobante al cliente que corre después de enviar la respuesta, espera medio segundo sin bloquear el servidor y escribe un mensaje con el id de la venta en el registro visible con el arranque normal de uvicorn. Una venta rechazada MUST NOT generar aviso.

#### Scenario: Aviso tras la respuesta
- **WHEN** se registra una venta válida con uvicorn arrancado normalmente
- **THEN** la consola muestra la línea de la respuesta 201 y, después, el mensaje del comprobante de esa venta

#### Scenario: Sin aviso en una venta rechazada
- **WHEN** una venta responde 409
- **THEN** la consola no muestra ningún mensaje de comprobante para esa petición

### Requirement: Listado de ventas
`GET /ventas` (VENDEDOR, ADMIN) SHALL responder el envoltorio de paginación de todas las ventas ordenadas por `id`, cada una con `id`, `fecha`, `total` y su cliente.

#### Scenario: Listado paginado
- **WHEN** el personal pide `GET /ventas?size=1`
- **THEN** responde 200 con un item y `total` igual a la cantidad de ventas

#### Scenario: Cliente pide el listado
- **WHEN** un usuario con sólo CLIENTE pide `GET /ventas`
- **THEN** responde 403

### Requirement: Detalle de venta para el personal o el dueño
`GET /ventas/{id}` SHALL pedir sesión pero no un rol: el personal (VENDEDOR o ADMIN vigente) MUST ver cualquier venta, y un usuario sin rol de personal MUST ver sólo las ventas de la ficha de cliente vinculada a su usuario; cualquier otra venta MUST responder 403 sin datos de la venta. Una venta inexistente MUST responder 404. El detalle MUST incluir el cliente, los renglones y el título de cada libro, aunque el libro esté dado de baja.

#### Scenario: La cliente ve su venta
- **WHEN** una usuaria con sólo CLIENTE pide el detalle de una venta de su ficha de cliente
- **THEN** responde 200 con la venta

#### Scenario: La cliente no ve la ajena
- **WHEN** la misma usuaria pide el detalle de una venta de otro cliente
- **THEN** responde 403

#### Scenario: Personal ve cualquier venta
- **WHEN** un VENDEDOR pide el detalle de cualquier venta existente
- **THEN** responde 200

#### Scenario: Venta inexistente
- **WHEN** un usuario con sesión pide `GET /ventas/9999`
- **THEN** responde 404

### Requirement: Mis ventas
`GET /mis-ventas` SHALL pedir sólo sesión y responder el envoltorio de paginación de las ventas de la ficha de cliente vinculada al usuario, ordenadas por `id`. Un usuario sin ficha de cliente MUST recibir una página vacía.

#### Scenario: Cliente con compras
- **WHEN** una usuaria CLIENTE con una venta pide `GET /mis-ventas`
- **THEN** responde 200 con esa venta y ninguna de otros clientes

#### Scenario: Personal sin ficha de cliente
- **WHEN** un VENDEDOR sin ficha de cliente pide `GET /mis-ventas`
- **THEN** responde 200 con `items` vacío y `total` 0

#### Scenario: Sin sesión
- **WHEN** se pide `GET /mis-ventas` sin cookie
- **THEN** responde 401
