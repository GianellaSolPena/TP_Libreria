-- Caso C-14: movimiento_stock es de solo agregado (disparador de la migracion 0004).
-- Uso: psql -v ON_ERROR_STOP=0 -f test/solo_agregado.sql
-- Autocontenido: crea su propia fixture dentro de una transaccion y termina con ROLLBACK,
-- asi que funciona con o sin seed.py y no deja filas.

BEGIN;

SELECT count(*) AS movimientos_antes FROM movimiento_stock;

-- Fixture propia (valores completos: no hay defaults en la base).
INSERT INTO usuario (id, email, nombre, password_hash, activo, debe_cambiar_password)
VALUES (900001, 'solo_agregado@prueba.local', 'Prueba', 'x', true, false);
INSERT INTO editorial (id, nombre, pais) VALUES (900001, 'Editorial solo_agregado', 'AR');
INSERT INTO libro (id, isbn, titulo, precio, stock, editorial_id)
VALUES (900001, 'SOLO-AGREGADO-1', 'Libro de prueba', 10.00, 1, 900001);
INSERT INTO movimiento_stock (id, libro_id, venta_id, usuario_id, cantidad, motivo, cuando)
VALUES (900001, 900001, NULL, 900001, 1, 'Stock inicial de prueba', now());

-- 1) INSERT permitido. Esperado: INSERT 0 1 (sin error).
INSERT INTO movimiento_stock (id, libro_id, venta_id, usuario_id, cantidad, motivo, cuando)
VALUES (900002, 900001, NULL, 900001, 2, 'Reposicion de prueba', now());

-- 2) UPDATE rechazado.
-- Esperado: ERROR:  movimiento_stock es de solo agregado: UPDATE no permitido
SAVEPOINT antes_update;
UPDATE movimiento_stock SET cantidad = 99 WHERE id = 900001;
ROLLBACK TO SAVEPOINT antes_update;

-- 3) DELETE rechazado.
-- Esperado: ERROR:  movimiento_stock es de solo agregado: DELETE no permitido
SAVEPOINT antes_delete;
DELETE FROM movimiento_stock WHERE id = 900001;
ROLLBACK TO SAVEPOINT antes_delete;

-- La fila sigue igual. Esperado: cantidad = 1.
SELECT id, cantidad FROM movimiento_stock WHERE id = 900001;

ROLLBACK;

-- Tras el ROLLBACK la base queda como estaba. Esperado: mismo valor que movimientos_antes.
SELECT count(*) AS movimientos_despues FROM movimiento_stock;
