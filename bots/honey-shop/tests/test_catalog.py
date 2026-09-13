# bots/honey-shop/tests/test_catalog.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from catalog import CATALOG, get_product


class TestCatalog(unittest.TestCase):
    def test_has_four_products(self):
        self.assertEqual(len(CATALOG), 4)

    def test_known_prices(self):
        prices = {p.name: p.price for p in CATALOG}
        self.assertEqual(
            prices,
            {
                "Липовый 1 литр": 60,
                "Гречишный 1 литр": 70,
                "Цветочный 1 литр": 55,
                "Разнотравье 1 литр": 65,
            },
        )

    def test_get_product_found(self):
        product = get_product(1)
        self.assertEqual(product.name, "Липовый 1 литр")

    def test_get_product_missing(self):
        self.assertIsNone(get_product(999))


if __name__ == "__main__":
    unittest.main()
