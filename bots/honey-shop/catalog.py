"""Фиксированный каталог мёда для тестового магазина."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: int  # Telegram Stars


CATALOG = [
    Product(1, "Липовый", 60),
    Product(2, "Гречишный", 70),
    Product(3, "Цветочный", 55),
    Product(4, "Разнотравье", 65),
]

_BY_ID = {p.id: p for p in CATALOG}


def get_product(product_id):
    return _BY_ID.get(product_id)
