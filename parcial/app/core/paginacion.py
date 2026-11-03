import math
from dataclasses import dataclass
from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel

T = TypeVar("T")

MAX_PAGE = 2**31 - 1


def calcular_paginas(total: int, size: int) -> int:
    return max(1, math.ceil(total / size))


def calcular_offset(page: int, size: int) -> int:
    return (page - 1) * size


@dataclass
class ParametrosPagina:
    page: Annotated[int, Query(ge=1, le=MAX_PAGE)] = 1
    size: Annotated[int, Query(ge=1, le=100)] = 20

    @property
    def offset(self) -> int:
        return calcular_offset(self.page, self.size)


PaginaDep = Annotated[ParametrosPagina, Depends()]


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int
