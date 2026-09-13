"""Фиксированный каталог мёда для тестового магазина."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: int  # Telegram Stars


CATALOG = [
    Product(1, "Липовый 1 литр", 60),
    Product(2, "Гречишный 1 литр", 70),
    Product(3, "Цветочный 1 литр", 55),
    Product(4, "Разнотравье 1 литр", 65),
]

_BY_ID = {p.id: p for p in CATALOG}


def get_product(product_id):
    return _BY_ID.get(product_id)
