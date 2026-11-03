from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import HTTPException, Path, status
from sqlalchemy.exc import IntegrityError

UNIQUE_VIOLATION = "23505"
FOREIGN_KEY_VIOLATION = "23503"
MENSAJE_GENERICO = "Los datos violan una restricción"

# Ids de ruta: serial (>= 1) y dentro de int4 para no llegar a la base con un valor imposible.
IdPath = Annotated[int, Path(ge=1, le=2_147_483_647)]


class NoEncontrado(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class Conflicto(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class PaginaInexistente(Exception):
    def __init__(self, page: int, pages: int) -> None:
        super().__init__(f"La página {page} no existe: hay {pages}")
        self.page = page
        self.pages = pages


@contextmanager
def traducir_errores(conflicto: str, conflicto_fk: str | None = None) -> Iterator[None]:
    """Traduce errores de dominio y de la base a HTTP, sin usar el texto de la base."""
    try:
        yield
    except NoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, exc.mensaje) from exc
    except Conflicto as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, exc.mensaje) from exc
    except PaginaInexistente as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"La página {exc.page} no existe: hay {exc.pages}",
        ) from exc
    except IntegrityError as exc:
        sqlstate = getattr(exc.orig, "sqlstate", None)
        if sqlstate == UNIQUE_VIOLATION:
            detalle = conflicto
        elif sqlstate == FOREIGN_KEY_VIOLATION and conflicto_fk is not None:
            detalle = conflicto_fk
        else:
            detalle = MENSAJE_GENERICO
        raise HTTPException(status.HTTP_409_CONFLICT, detalle) from None
