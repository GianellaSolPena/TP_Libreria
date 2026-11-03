"""disparador solo agregado

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03

Escrita A MANO: la comparacion automatica de Alembic (autogenerate) no ve
funciones ni disparadores, asi que no puede generar esta migracion. Fue
revisada contra el diseno (D-10) antes de aplicarse.

`movimiento_stock` es de solo agregado: la base rechaza todo UPDATE y todo
DELETE, venga de la aplicacion, de psql o de cualquier otro cliente. INSERT
sigue permitido. El disparador es POR FILA (`FOR EACH ROW`), por lo que
TRUNCATE (usado por `seed.py`) no queda bloqueado. El error lleva
ERRCODE `restrict_violation` para que la aplicacion pueda traducirlo.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION movimiento_stock_solo_agregado() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'movimiento_stock es de solo agregado: % no permitido', TG_OP
            USING ERRCODE = 'restrict_violation';
        END $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER tg_movimiento_stock_solo_agregado
          BEFORE UPDATE OR DELETE ON movimiento_stock
          FOR EACH ROW EXECUTE FUNCTION movimiento_stock_solo_agregado()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS tg_movimiento_stock_solo_agregado ON movimiento_stock"
    )
    op.execute("DROP FUNCTION IF EXISTS movimiento_stock_solo_agregado()")
