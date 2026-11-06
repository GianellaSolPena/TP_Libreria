import math
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any

from fastapi import HTTPException, Path, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError

UNIQUE_VIOLATION = "23505"
FOREIGN_KEY_VIOLATION = "23503"
NUMERIC_VALUE_OUT_OF_RANGE = "22003"
# Errores de dato de la base atribuibles a la entrada del cliente (lista explícita, no toda la clase 22).
DATO_INVALIDO = frozenset(
    {
        "22021",  # character_not_in_repertoire (p. ej. 0x00 en UTF-8)
        "22P05",  # untranslatable_character
        "22P02",  # invalid_text_representation
        "22001",  # string_data_right_truncation
        "22007",  # invalid_datetime_format
        "22008",  # datetime_field_overflow
    }
)
MENSAJE_GENERICO = "Los datos violan una restricción"
MENSAJE_DESBORDE = "El valor supera el máximo permitido"
MENSAJE_DATO_INVALIDO = "Algún dato enviado no es válido"

# Ids de ruta: serial (>= 1) y dentro de int4 para no llegar a la base con un valor imposible.
IdPath = Annotated[int, Path(ge=1, le=2_147_483_647)]


def _serializable(valor: Any) -> Any:
    """Deja la entrada repetida en el 422 apta para JSON/UTF-8; para lo demás es la identidad.

    Un `float` no finito (NaN, Infinity, 1e400) pasa a su texto y un sustituto UTF-16 suelto
    pasa a su escape visible (`\\ud800`); en ambos casos la respuesta estándar no se podía
    serializar y terminaba en 500.
    """
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else str(valor)
    if isinstance(valor, str):
        try:
            valor.encode("utf-8")
        except UnicodeEncodeError:
            return valor.encode("utf-8", "backslashreplace").decode("utf-8")
        return valor
    if isinstance(valor, dict):
        return {_serializable(k): _serializable(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_serializable(v) for v in valor]
    return valor


async def validacion_a_422(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Mismo 422 que el de FastAPI (`{"detail": [...]}`), pero siempre serializable (RN-15)."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": _serializable(jsonable_encoder(exc.errors()))},
    )


class NoEncontrado(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class Conflicto(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class SinPermiso(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class PaginaInexistente(Exception):
    def __init__(self, page: int, pages: int) -> None:
        super().__init__(f"La página {page} no existe: hay {pages}")
        self.page = page
        self.pages = pages


class CredencialesInvalidas(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class DemasiadosIntentos(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Demasiados intentos fallidos")
        self.retry_after = retry_after


def _no_se_pudo_codificar(error: BaseException | None) -> bool:
    """True si el driver falló al codificar un texto de la entrada (p. ej. un sustituto suelto).

    asyncpg lo informa como `DataError` sin SQLSTATE; se reconoce por la causa
    (`UnicodeEncodeError` en la cadena `__cause__`/`__context__`), no por el texto del mensaje.
    """
    visto: set[int] = set()
    while error is not None and id(error) not in visto:
        if isinstance(error, UnicodeEncodeError):
            return True
        visto.add(id(error))
        error = error.__cause__ or error.__context__
    return False


@contextmanager
def traducir_errores(conflicto: str, conflicto_fk: str | None = None) -> Iterator[None]:
    """Traduce errores de dominio y de la base a HTTP, sin usar el texto de la base."""
    try:
        yield
    except NoEncontrado as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, exc.mensaje) from exc
    except Conflicto as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, exc.mensaje) from exc
    except SinPermiso as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, exc.mensaje) from exc
    except PaginaInexistente as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"La página {exc.page} no existe: hay {exc.pages}",
        ) from exc
    except CredencialesInvalidas as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, exc.mensaje) from exc
    except DemasiadosIntentos as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Demasiados intentos fallidos; probá de nuevo más tarde",
            headers={"Retry-After": str(exc.retry_after)},
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
    except DBAPIError as exc:
        # IntegrityError ya se atendió arriba; de los demás, el desborde numérico (409) y los
        # datos inválidos de la entrada (422) son del cliente. Cualquier otro error de la base
        # se propaga (500 sin texto de la base). El texto que el driver no puede codificar es del cliente.
        sqlstate = getattr(exc.orig, "sqlstate", None)
        if sqlstate == NUMERIC_VALUE_OUT_OF_RANGE:
            raise HTTPException(status.HTTP_409_CONFLICT, MENSAJE_DESBORDE) from None
        if sqlstate in DATO_INVALIDO or _no_se_pudo_codificar(exc.orig):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, MENSAJE_DATO_INVALIDO) from None
        raise
