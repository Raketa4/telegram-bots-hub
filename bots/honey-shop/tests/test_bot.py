# bots/honey-shop/tests/test_bot.py
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bot
import cart
import checkout


class FakeApi:
    """Заменяет bot.api: пишет вызовы в список, ничего не отправляет по сети."""

    def __init__(self):
        self.calls = []

    def __call__(self, token, method, **params):
        self.calls.append((method, params))
        if method == "answerPreCheckoutQuery":
            return {"ok": True}
        return {"ok": True, "result": {}}

    def last(self, method):
        for m, params in reversed(self.calls):
            if m == method:
                return params
        return None


class TestBotHandleUpdate(unittest.TestCase):
    TOKEN = "test-token"
    CHAT_ID = 111
    USER = {"id": 111, "username": "buyer"}

    def setUp(self):
        self.fake_api = FakeApi()
        self.orig_api = bot.api
        bot.api = self.fake_api
        bot.carts.clear()
        bot.checkout_state.clear()
        # Redirect order storage to a throwaway file so tests never touch
        # the real orders.jsonl (which may hold real personal data).
        fd, self.orders_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        self.orig_orders_file = bot.ORDERS_FILE
        bot.ORDERS_FILE = self.orders_path

    def tearDown(self):
        bot.api = self.orig_api
        bot.ORDERS_FILE = self.orig_orders_file
        os.remove(self.orders_path)

    def _message(self, text):
        return {
            "message": {
                "chat": {"id": self.CHAT_ID},
                "from": self.USER,
                "text": text,
            }
        }

    def test_start_shows_test_store_warning(self):
        bot.handle_update(self.TOKEN, self._message("/start"))
        params = self.fake_api.last("sendMessage")
        self.assertIn("тестовый магазин", params["text"])

    def test_add_to_cart_via_callback(self):
        update = {
            "callback_query": {
                "id": "cbq1",
                "from": self.USER,
                "data": "add:1",
                "message": {"chat": {"id": self.CHAT_ID}},
            }
        }
        bot.handle_update(self.TOKEN, update)
        self.assertEqual(bot.carts[self.USER["id"]], {1: 1})

    def test_checkout_sends_invoice_in_stars(self):
        bot.carts[self.USER["id"]] = {1: 2}  # Липовый x2 = 120
        update = {
            "callback_query": {
                "id": "cbq2",
                "from": self.USER,
                "data": "checkout",
                "message": {"chat": {"id": self.CHAT_ID}},
            }
        }
        bot.handle_update(self.TOKEN, update)
        params = self.fake_api.last("sendInvoice")
        self.assertEqual(params["currency"], "XTR")
        self.assertEqual(sum(p["amount"] for p in params["prices"]), 120)

    def test_pre_checkout_ok_when_payload_matches(self):
        payload = cart.build_payload({1: 1})  # 60 Stars
        update = {
            "pre_checkout_query": {
                "id": "pcq1",
                "from": self.USER,
                "invoice_payload": payload,
                "total_amount": 60,
                "currency": "XTR",
            }
        }
        bot.handle_update(self.TOKEN, update)
        params = self.fake_api.last("answerPreCheckoutQuery")
        self.assertTrue(params["ok"])

    def test_pre_checkout_rejects_amount_mismatch(self):
        payload = cart.build_payload({1: 1})  # 60 Stars
        update = {
            "pre_checkout_query": {
                "id": "pcq2",
                "from": self.USER,
                "invoice_payload": payload,
                "total_amount": 999,
                "currency": "XTR",
            }
        }
        bot.handle_update(self.TOKEN, update)
        params = self.fake_api.last("answerPreCheckoutQuery")
        self.assertFalse(params["ok"])

    def test_successful_payment_starts_address_prompt(self):
        payload = cart.build_payload({1: 1})
        bot.carts[self.USER["id"]] = {1: 1}
        update = {
            "message": {
                "chat": {"id": self.CHAT_ID},
                "from": self.USER,
                "successful_payment": {
                    "currency": "XTR",
                    "total_amount": 60,
                    "invoice_payload": payload,
                    "telegram_payment_charge_id": "charge123",
                },
            }
        }
        bot.handle_update(self.TOKEN, update)
        self.assertNotIn(self.USER["id"], bot.carts)
        entry = bot.checkout_state[self.USER["id"]]
        self.assertEqual(entry["state"], checkout.STATE_AWAITING_ADDRESS)
        params = self.fake_api.last("sendMessage")
        self.assertIn("адрес", params["text"].lower())

    def test_checkout_blank_address_reprompts_without_advancing(self):
        payload = cart.build_payload({1: 1})
        bot.carts[self.USER["id"]] = {1: 1}
        bot.handle_update(self.TOKEN, {
            "message": {
                "chat": {"id": self.CHAT_ID},
                "from": self.USER,
                "successful_payment": {
                    "currency": "XTR",
                    "total_amount": 60,
                    "invoice_payload": payload,
                    "telegram_payment_charge_id": "charge123",
                },
            }
        })
        bot.handle_update(self.TOKEN, self._message("   "))
        entry = bot.checkout_state[self.USER["id"]]
        self.assertEqual(entry["state"], checkout.STATE_AWAITING_ADDRESS)
        self.assertIsNone(entry["address"])
        params = self.fake_api.last("sendMessage")
        self.assertIn("пуст", params["text"].lower())

    def test_full_checkout_writes_order_and_confirms(self):
        payload = cart.build_payload({1: 1})
        bot.carts[self.USER["id"]] = {1: 1}
        bot.handle_update(self.TOKEN, {
            "message": {
                "chat": {"id": self.CHAT_ID},
                "from": self.USER,
                "successful_payment": {
                    "currency": "XTR",
                    "total_amount": 60,
                    "invoice_payload": payload,
                    "telegram_payment_charge_id": "charge123",
                },
            }
        })
        bot.handle_update(self.TOKEN, self._message("ПВЗ Ozon, ул. Тестовая 1"))
        self.assertEqual(
            bot.checkout_state[self.USER["id"]]["state"], checkout.STATE_AWAITING_PHONE
        )
        bot.handle_update(self.TOKEN, self._message("+79990001122"))
        self.assertNotIn(self.USER["id"], bot.checkout_state)
        params = self.fake_api.last("sendMessage")
        self.assertIn("тест", params["text"].lower())

    def test_liters_text_pluralization(self):
        self.assertEqual(bot.liters_text(1), "1 литр")
        self.assertEqual(bot.liters_text(2), "2 литра")
        self.assertEqual(bot.liters_text(4), "4 литра")
        self.assertEqual(bot.liters_text(5), "5 литров")
        self.assertEqual(bot.liters_text(11), "11 литров")
        self.assertEqual(bot.liters_text(21), "21 литр")

    def test_shop_view_shows_liters_not_multiplier(self):
        bot.carts[self.USER["id"]] = {1: 1}
        update = {
            "callback_query": {
                "id": "cbq3",
                "from": self.USER,
                "data": "add:1",
                "message": {"chat": {"id": self.CHAT_ID}},
            }
        }
        bot.handle_update(self.TOKEN, update)
        params = self.fake_api.last("sendMessage")
        self.assertIn("2 литра", params["text"])
        self.assertNotIn("×2", params["text"])

    def test_shop_text_shows_liters_and_total(self):
        text = bot.shop_text({1: 2})  # Липовый, qty 2, 60⭐ each
        self.assertIn("2 литра", text)
        self.assertIn("120", text)

    def test_shop_text_empty_cart(self):
        text = bot.shop_text({})
        self.assertIn("Выберите", text)

    def test_can_add_second_variety_directly_from_shop_view(self):
        bot.carts[self.USER["id"]] = {1: 1}
        update = {
            "callback_query": {
                "id": "cbq6",
                "from": self.USER,
                "data": "add:2",
                "message": {"chat": {"id": self.CHAT_ID}},
            }
        }
        bot.handle_update(self.TOKEN, update)
        self.assertEqual(bot.carts[self.USER["id"]], {1: 1, 2: 1})
        params = self.fake_api.last("sendMessage")
        self.assertIn("Гречишный", params["text"])
        self.assertIn("Липовый", params["text"])

    def test_add_to_cart_edits_existing_message_when_message_id_present(self):
        bot.carts[self.USER["id"]] = {}
        update = {
            "callback_query": {
                "id": "cbq4",
                "from": self.USER,
                "data": "add:1",
                "message": {"chat": {"id": self.CHAT_ID}, "message_id": 555},
            }
        }
        bot.handle_update(self.TOKEN, update)
        params = self.fake_api.last("editMessageText")
        self.assertIsNotNone(params)
        self.assertEqual(params["message_id"], 555)
        self.assertIn("1 литр", params["text"])
        self.assertIsNone(self.fake_api.last("sendMessage"))

    def test_add_to_cart_sends_new_message_when_no_message_id(self):
        bot.carts[self.USER["id"]] = {}
        update = {
            "callback_query": {
                "id": "cbq5",
                "from": self.USER,
                "data": "add:1",
                "message": {"chat": {"id": self.CHAT_ID}},
            }
        }
        bot.handle_update(self.TOKEN, update)
        self.assertIsNone(self.fake_api.last("editMessageText"))
        params = self.fake_api.last("sendMessage")
        self.assertIn("1 литр", params["text"])


if __name__ == "__main__":
    unittest.main()
