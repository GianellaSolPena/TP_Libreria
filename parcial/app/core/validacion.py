from typing import Annotated

from pydantic import AfterValidator, StringConstraints


def rechazar_nulo(valor: str) -> str:
    """PostgreSQL no admite U+0000 en text/varchar: se rechaza en el contrato (422)."""
    if "\x00" in valor:
        raise ValueError("El texto no puede contener el carácter nulo (U+0000)")
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
