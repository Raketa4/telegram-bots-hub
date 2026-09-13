import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cart import (
    add_item,
    build_payload,
    cart_lines,
    cart_total,
    items_from_cart,
    parse_payload,
    remove_item,
    total_for_items,
)


class TestCart(unittest.TestCase):
    def test_add_item_new(self):
        cart = {}
        add_item(cart, 1)
        self.assertEqual(cart, {1: 1})

    def test_add_item_existing_increments(self):
        cart = {1: 2}
        add_item(cart, 1)
        self.assertEqual(cart, {1: 3})

    def test_remove_item_decrements(self):
        cart = {1: 2}
        remove_item(cart, 1)
        self.assertEqual(cart, {1: 1})

    def test_remove_item_drops_at_zero(self):
        cart = {1: 1}
        remove_item(cart, 1)
        self.assertEqual(cart, {})

    def test_remove_item_missing_is_noop(self):
        cart = {}
        remove_item(cart, 1)
        self.assertEqual(cart, {})

    def test_cart_lines_and_total(self):
        cart = {1: 2, 3: 1}  # Липовый(60) x2 + Цветочный(55) x1
        lines = cart_lines(cart)
        self.assertEqual(len(lines), 2)
        self.assertEqual(cart_total(cart), 60 * 2 + 55)

    def test_cart_lines_skips_unknown_product(self):
        cart = {999: 1}
        self.assertEqual(cart_lines(cart), [])
        self.assertEqual(cart_total(cart), 0)

    def test_payload_roundtrip(self):
        cart = {1: 2, 2: 1}
        payload = build_payload(cart)
        items = parse_payload(payload)
        self.assertEqual(sorted(items), [(1, 2), (2, 1)])

    def test_total_for_items_matches_cart_total(self):
        cart = {1: 2, 2: 1}
        items = items_from_cart(cart)
        self.assertEqual(total_for_items(items), cart_total(cart))

    def test_parse_payload_garbage_returns_empty(self):
        self.assertEqual(parse_payload("not json"), [])
        self.assertEqual(parse_payload("{}"), [])


if __name__ == "__main__":
    unittest.main()
