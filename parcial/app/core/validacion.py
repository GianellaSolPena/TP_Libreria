from typing import Annotated

from pydantic import AfterValidator, StringConstraints


def rechazar_nulo(valor: str) -> str:
    """Rechaza en el contrato (422) los textos que la base no puede guardar.

    PostgreSQL no admite U+0000 en text/varchar, y un sustituto UTF-16 suelto (U+D800-U+DFFF)
    no se puede codificar en UTF-8 (ni para la base ni para repetirlo en la respuesta).
    Un par válido (p. ej. un emoji) llega como un solo punto de código y no se ve afectado.
    """
    if "\x00" in valor:
        raise ValueError("El texto no puede contener el carácter nulo (U+0000)")
    if any("\ud800" <= c <= "\udfff" for c in valor):
        raise ValueError("El texto no puede contener sustitutos UTF-16 sueltos (U+D800 a U+DFFF)")
    return valor


def _normalizar_email(valor: str) -> str:
    return valor.strip().lower()


TextoSinNulo = Annotated[str, AfterValidator(rechazar_nulo)]

# Un solo tipo de correo para cuentas y clientes: se recorta y pasa a minusculas para que
# Ana@Example.com y ana@example.com no sean dos cuentas, dos fichas ni dos contadores
# (RN-02: si ya existe un cliente con ese correo, el registro da 409).
Email = Annotated[
    str,
    AfterValidator(rechazar_nulo),
    StringConstraints(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$"),
    AfterValidator(_normalizar_email),
]
