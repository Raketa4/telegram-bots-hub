# bots/honey-shop/tests/test_checkout.py
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import checkout


class TestCheckout(unittest.TestCase):
    def test_start_checkout_snapshots_cart(self):
        entry = checkout.start_checkout({1: 2, 3: 1})  # Липовый x2 + Цветочный x1
        self.assertEqual(entry["state"], checkout.STATE_AWAITING_ADDRESS)
        self.assertEqual(entry["total"], 60 * 2 + 55)
        self.assertEqual(len(entry["items"]), 2)
        self.assertIsNone(entry["address"])
        self.assertIsNone(entry["phone"])

    def test_add_address_advances_state(self):
        entry = checkout.start_checkout({1: 1})
        checkout.add_address(entry, "  ПВЗ Ozon, ул. Пушкина 1  ")
        self.assertEqual(entry["address"], "ПВЗ Ozon, ул. Пушкина 1")
        self.assertEqual(entry["state"], checkout.STATE_AWAITING_PHONE)

    def test_add_phone_completes(self):
        entry = checkout.start_checkout({1: 1})
        checkout.add_address(entry, "ПВЗ Ozon")
        checkout.add_phone(entry, " +79990001122 ")
        self.assertEqual(entry["phone"], "+79990001122")
        self.assertEqual(entry["state"], checkout.STATE_NONE)
        self.assertTrue(checkout.is_complete(entry))

    def test_is_complete_false_before_phone(self):
        entry = checkout.start_checkout({1: 1})
        self.assertFalse(checkout.is_complete(entry))
        checkout.add_address(entry, "ПВЗ Ozon")
        self.assertFalse(checkout.is_complete(entry))

    def test_to_order_record_shape(self):
        entry = checkout.start_checkout({1: 2})
        checkout.add_address(entry, "ПВЗ Ozon")
        checkout.add_phone(entry, "+79990001122")
        record = checkout.to_order_record(42, "ivan", entry)
        self.assertEqual(record["user_id"], 42)
        self.assertEqual(record["username"], "ivan")
        self.assertEqual(record["total_stars"], 120)
        self.assertEqual(record["pvz_address"], "ПВЗ Ozon")
        self.assertEqual(record["phone"], "+79990001122")
        self.assertIn("created_at", record)

    def test_add_address_blank_does_not_advance(self):
        entry = checkout.start_checkout({1: 1})
        checkout.add_address(entry, "   ")
        self.assertEqual(entry["state"], checkout.STATE_AWAITING_ADDRESS)
        self.assertIsNone(entry["address"])

    def test_add_phone_blank_does_not_advance(self):
        entry = checkout.start_checkout({1: 1})
        checkout.add_address(entry, "ПВЗ Ozon")
        checkout.add_phone(entry, "   ")
        self.assertEqual(entry["state"], checkout.STATE_AWAITING_PHONE)
        self.assertIsNone(entry["phone"])


if __name__ == "__main__":
    unittest.main()
