from typing import Annotated

from pydantic import AfterValidator


def rechazar_nulo(valor: str) -> str:
    """PostgreSQL no admite U+0000 en text/varchar: se rechaza en el contrato (422)."""
    if "\x00" in valor:
        raise ValueError("El texto no puede contener el carácter nulo (U+0000)")
    return valor


TextoSinNulo = Annotated[str, AfterValidator(rechazar_nulo)]
