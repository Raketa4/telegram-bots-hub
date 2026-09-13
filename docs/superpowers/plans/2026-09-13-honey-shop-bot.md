# Honey Shop Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that runs a test honey shop — cart-based catalog, payment in Telegram Stars (XTR), and post-payment collection of Ozon pickup-point delivery details — reusing the proven stdlib long-polling pattern from `C:\Users\Андрей\Potsyk\bot\bot.py`.

**Architecture:** Pure Python 3 standard library, no pip dependencies. Three small pure-logic modules (`catalog.py`, `cart.py`, `checkout.py`) hold all business logic and are unit-tested without any network access. `bot.py` is the thin Telegram wiring layer (long polling via `urllib`, `api()`/`log()`/`load_env()` ported near-verbatim from the Potsyk bot) that calls into those modules and is itself tested offline via a monkeypatched `api()`.

**Tech Stack:** Python 3 (stdlib only: `urllib`, `json`, `dataclasses`, `datetime`, `unittest`), Windows Task Scheduler for autostart, plain HTML/JS for the one line touched in the existing site hub.

**Spec:** `docs/superpowers/specs/2026-09-13-honey-shop-bot-design.md`

## Global Constraints

- No third-party packages, no venv — stdlib only (spec: Архитектура).
- Bot lives at `bots/honey-shop/` inside the `telegram-bots-hub` repo; `bot.py` itself must contain no Windows-specific or absolute paths (spec: Цель).
- Currency is always `XTR` (Telegram Stars) (spec: Пользовательский флоу, шаг 4).
- Catalog is exactly: Липовый 60⭐, Гречишный 70⭐, Цветочный 55⭐, Разнотравье 65⭐ (spec: Каталог товаров).
- `/start` greeting must literally contain: "⚠️ Это тестовый магазин. Реальный товар не отправляется." (spec: Пользовательский флоу, шаг 1).
- Secrets and personal data never committed: `.env`, `bot.log`, `orders.jsonl` are gitignored (spec: Логирование и хранение данных).
- `/paysupport` command is required by Telegram whenever a bot accepts payments (spec: Команды).

---

### Task 1: Catalog module

**Files:**
- Create: `bots/honey-shop/catalog.py`
- Test: `bots/honey-shop/tests/__init__.py` (empty, makes `tests` an importable package for `unittest discover`)
- Test: `bots/honey-shop/tests/test_catalog.py`

**Interfaces:**
- Produces: `Product` (dataclass: `id: int`, `name: str`, `price: int`), `CATALOG: list[Product]`, `get_product(product_id: int) -> Product | None`

- [ ] **Step 1: Write the failing test**

```python
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
            {"Липовый": 60, "Гречишный": 70, "Цветочный": 55, "Разнотравье": 65},
        )

    def test_get_product_found(self):
        product = get_product(1)
        self.assertEqual(product.name, "Липовый")

    def test_get_product_missing(self):
        self.assertIsNone(get_product(999))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Note: `bots/honey-shop` has a hyphen, so it cannot be addressed as a
dotted Python module path (`bots.honey-shop...` is invalid syntax).
Every test in this plan is instead run directly by file path.

Run (from repo root `C:\Users\Андрей\telegram-bots-hub`):
`py -3.14 bots/honey-shop/tests/test_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'catalog'`.

- [ ] **Step 3: Write minimal implementation**

```python
# bots/honey-shop/catalog.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.14 bots/honey-shop/tests/test_catalog.py -v`
Expected: PASS (4 tests, ok)

- [ ] **Step 5: Commit**

```bash
git add bots/honey-shop/catalog.py bots/honey-shop/tests/__init__.py bots/honey-shop/tests/test_catalog.py
git commit -m "Add honey shop catalog module"
```

---

### Task 2: Cart module

**Files:**
- Create: `bots/honey-shop/cart.py`
- Test: `bots/honey-shop/tests/test_cart.py`

**Interfaces:**
- Consumes: `catalog.get_product(product_id) -> Product | None` (Task 1)
- Produces: `add_item(cart: dict, product_id: int, qty: int = 1) -> dict`, `remove_item(cart: dict, product_id: int, qty: int = 1) -> dict`, `cart_lines(cart: dict) -> list[tuple[Product, int, int]]` (product, qty, subtotal), `cart_total(cart: dict) -> int`, `items_from_cart(cart: dict) -> list[list[int]]` (`[[product_id, qty], ...]`), `total_for_items(items: list) -> int`, `build_payload(cart: dict) -> str` (JSON), `parse_payload(payload: str) -> list[tuple[int, int]]`

- [ ] **Step 1: Write the failing test**

```python
# bots/honey-shop/tests/test_cart.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.14 bots/honey-shop/tests/test_cart.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cart'`.

- [ ] **Step 3: Write minimal implementation**

```python
# bots/honey-shop/cart.py
"""Чистая логика корзины: без сети, без Telegram, легко тестируется."""

import json

from catalog import get_product


def add_item(cart, product_id, qty=1):
    cart[product_id] = cart.get(product_id, 0) + qty
    return cart


def remove_item(cart, product_id, qty=1):
    if product_id not in cart:
        return cart
    remaining = cart[product_id] - qty
    if remaining <= 0:
        del cart[product_id]
    else:
        cart[product_id] = remaining
    return cart


def cart_lines(cart):
    lines = []
    for product_id, qty in cart.items():
        product = get_product(product_id)
        if product is None or qty <= 0:
            continue
        lines.append((product, qty, product.price * qty))
    return lines


def cart_total(cart):
    return sum(subtotal for _, _, subtotal in cart_lines(cart))


def items_from_cart(cart):
    return [[product_id, qty] for product_id, qty in cart.items() if qty > 0]


def total_for_items(items):
    return cart_total({product_id: qty for product_id, qty in items})


def build_payload(cart):
    return json.dumps({"items": items_from_cart(cart)})


def parse_payload(payload):
    try:
        data = json.loads(payload)
        return [(int(pid), int(qty)) for pid, qty in data.get("items", [])]
    except (ValueError, TypeError, KeyError):
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.14 bots/honey-shop/tests/test_cart.py -v`
Expected: PASS (10 tests, ok)

- [ ] **Step 5: Commit**

```bash
git add bots/honey-shop/cart.py bots/honey-shop/tests/test_cart.py
git commit -m "Add honey shop cart module"
```

---

### Task 3: Checkout state machine module

**Files:**
- Create: `bots/honey-shop/checkout.py`
- Test: `bots/honey-shop/tests/test_checkout.py`

**Interfaces:**
- Consumes: `cart.cart_lines(cart)`, `cart.cart_total(cart)` (Task 2)
- Produces: `STATE_AWAITING_ADDRESS`, `STATE_AWAITING_PHONE`, `STATE_NONE` (str constants), `start_checkout(cart: dict) -> dict` (entry), `add_address(entry: dict, text: str) -> dict`, `add_phone(entry: dict, text: str) -> dict`, `is_complete(entry: dict) -> bool`, `to_order_record(user_id: int, username: str, entry: dict) -> dict`

- [ ] **Step 1: Write the failing test**

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.14 bots/honey-shop/tests/test_checkout.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'checkout'`.

- [ ] **Step 3: Write minimal implementation**

```python
# bots/honey-shop/checkout.py
"""Состояние оформления заказа после оплаты: адрес ПВЗ -> телефон -> запись заказа."""

import datetime

from cart import cart_lines, cart_total

STATE_AWAITING_ADDRESS = "awaiting_address"
STATE_AWAITING_PHONE = "awaiting_phone"
STATE_NONE = "none"


def start_checkout(cart):
    lines = cart_lines(cart)
    return {
        "state": STATE_AWAITING_ADDRESS,
        "items": [
            {"product_id": p.id, "name": p.name, "qty": qty, "subtotal": subtotal}
            for p, qty, subtotal in lines
        ],
        "total": cart_total(cart),
        "address": None,
        "phone": None,
    }


def add_address(entry, text):
    text = text.strip()
    if not text:
        return entry  # blank input: stay in AWAITING_ADDRESS, caller re-prompts
    entry["address"] = text
    entry["state"] = STATE_AWAITING_PHONE
    return entry


def add_phone(entry, text):
    text = text.strip()
    if not text:
        return entry  # blank input: stay in AWAITING_PHONE, caller re-prompts
    entry["phone"] = text
    entry["state"] = STATE_NONE
    return entry


def is_complete(entry):
    return entry["state"] == STATE_NONE and bool(entry["address"]) and bool(entry["phone"])


def to_order_record(user_id, username, entry):
    return {
        "user_id": user_id,
        "username": username,
        "items": entry["items"],
        "total_stars": entry["total"],
        "pvz_address": entry["address"],
        "phone": entry["phone"],
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.14 bots/honey-shop/tests/test_checkout.py -v`
Expected: PASS (7 tests, ok)

- [ ] **Step 5: Commit**

```bash
git add bots/honey-shop/checkout.py bots/honey-shop/tests/test_checkout.py
git commit -m "Add honey shop checkout state machine"
```

---

### Task 4: Bot wiring (`bot.py`) — Telegram API, keyboards, `handle_update`

**Files:**
- Create: `bots/honey-shop/bot.py`
- Test: `bots/honey-shop/tests/test_bot.py`

**Interfaces:**
- Consumes: `catalog.CATALOG`, `catalog.get_product` (Task 1); `cart.add_item`, `cart.remove_item`, `cart.cart_lines`, `cart.cart_total`, `cart.build_payload`, `cart.parse_payload`, `cart.total_for_items` (Task 2); `checkout.start_checkout`, `checkout.add_address`, `checkout.add_phone`, `checkout.STATE_AWAITING_ADDRESS`, `checkout.STATE_AWAITING_PHONE`, `checkout.to_order_record` (Task 3)
- Produces: `api(token, method, **params) -> dict`, `log(msg)`, `load_env()`, `handle_update(token, update)`, `main()` — module-level `carts: dict`, `checkout_state: dict`

This is the biggest task; it ports the proven Telegram plumbing from `C:\Users\Андрей\Potsyk\bot\bot.py` (`api`, `log`, `load_env`, the `getUpdates` loop in `main`) almost unchanged, and writes new routing in `handle_update` for the honey shop's cart/checkout flow. The test monkeypatches `api` at module level so no network call ever happens.

- [ ] **Step 1: Write the failing test**

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.14 bots/honey-shop/tests/test_bot.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot'`.

- [ ] **Step 3: Write minimal implementation**

```python
# bots/honey-shop/bot.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Телеграм-бот — тестовый магазин мёда с оплатой в Telegram Stars.

Только стандартная библиотека Python, приём обновлений через long polling.
Токен читается из TELEGRAM_BOT_TOKEN (переменная окружения или .env рядом
со скриптом).
"""

import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

from catalog import CATALOG, get_product
from cart import add_item, build_payload, cart_lines, cart_total, parse_payload, remove_item, total_for_items
import checkout

API_URL = "https://api.telegram.org/bot{token}/{method}"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log")
LOG_MAX_BYTES = 1_000_000
ORDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orders.jsonl")

START_TEXT = (
    "⚠️ Это тестовый магазин. Реальный товар не отправляется.\n\n"
    "Здесь можно \"купить\" мёд за настоящие Telegram Stars, чтобы "
    "посмотреть, как работает витрина, корзина и оплата.\n\n"
    "Откройте каталог, чтобы выбрать сорт мёда."
)

HELP_TEXT = (
    "Тестовый магазин мёда.\n\n"
    "/start — открыть каталог\n"
    "/paysupport — вопросы по оплате и возвратам\n\n"
    "⚠️ Это тестовый магазин, доставка не выполняется по-настоящему."
)

PAYSUPPORT_TEXT = (
    "Оплата проходит через Telegram Stars.\n\n"
    "Это тестовый магазин: возврат Stars возможен по запросу — пришлите "
    "в этот чат номер квитанции из сообщения об оплате.\n\n"
    "TODO: владельцу — обрабатывать возвраты методом refundStarPayment."
)

ASK_ADDRESS_TEXT = "Оплата прошла (⭐ {total} Stars)! Пришлите адрес пункта выдачи Ozon для доставки."
ASK_PHONE_TEXT = "Спасибо! Теперь пришлите номер телефона, привязанный к аккаунту Ozon."

carts = {}          # user_id -> {product_id: qty}
checkout_state = {}  # user_id -> entry dict from checkout.start_checkout()


def log(msg):
    line = "%s  %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        if sys.stdout is not None:
            print(line, flush=True)
    except Exception:  # noqa: BLE001
        pass
    try:
        if os.path.isfile(LOG_FILE) and os.path.getsize(LOG_FILE) > LOG_MAX_BYTES:
            backup = LOG_FILE + ".1"
            if os.path.exists(backup):
                os.remove(backup)
            os.replace(LOG_FILE, backup)
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def load_env():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def api(token, method, **params):
    url = API_URL.format(token=token, method=method)
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=65) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(body)
        except ValueError:
            parsed = {"ok": False, "error_code": exc.code, "description": body}
        if not (method == "getUpdates" and exc.code == 409):
            log("[api] %s -> HTTP %s: %s" % (method, exc.code, body[:300]))
        return parsed
    except Exception as exc:  # noqa: BLE001 — сеть капризна, продолжаем polling
        log("[api] %s -> %s" % (method, exc))
        return {"ok": False, "description": str(exc)}


def _who(obj):
    user = (obj or {}).get("from") or {}
    name = user.get("username") or user.get("first_name") or "?"
    return "%s (id %s)" % (name, user.get("id", "?"))


def catalog_keyboard():
    rows = [
        [{"text": "%s — %d ⭐" % (p.name, p.price), "callback_data": "add:%d" % p.id}]
        for p in CATALOG
    ]
    rows.append([{"text": "🧺 Корзина", "callback_data": "cart"}])
    return {"inline_keyboard": rows}


def cart_keyboard(cart):
    rows = []
    for product, qty, subtotal in cart_lines(cart):
        rows.append([
            {"text": "➖", "callback_data": "dec:%d" % product.id},
            {"text": "%s ×%d = %d⭐" % (product.name, qty, subtotal), "callback_data": "noop"},
            {"text": "➕", "callback_data": "inc:%d" % product.id},
        ])
    if cart:
        rows.append([{"text": "✅ Оформить заказ (%d ⭐)" % cart_total(cart), "callback_data": "checkout"}])
        rows.append([{"text": "🗑 Очистить корзину", "callback_data": "clear"}])
    rows.append([{"text": "🛍 Каталог", "callback_data": "catalog"}])
    return {"inline_keyboard": rows}


def send_start(token, chat_id):
    api(token, "sendMessage", chat_id=chat_id, text=START_TEXT, reply_markup=catalog_keyboard())


def send_catalog(token, chat_id):
    api(token, "sendMessage", chat_id=chat_id, text="Выберите сорт мёда:", reply_markup=catalog_keyboard())


def send_cart(token, chat_id, cart):
    if not cart_lines(cart):
        text = "Корзина пуста. Откройте каталог, чтобы что-то выбрать."
    else:
        text = "Ваша корзина:"
    api(token, "sendMessage", chat_id=chat_id, text=text, reply_markup=cart_keyboard(cart))


def send_invoice(token, chat_id, cart):
    lines = cart_lines(cart)
    api(
        token,
        "sendInvoice",
        chat_id=chat_id,
        title="Заказ мёда (тест)",
        description=", ".join("%s x%d" % (p.name, qty) for p, qty, _ in lines),
        payload=build_payload(cart),
        currency="XTR",
        prices=[{"label": "%s x%d" % (p.name, qty), "amount": subtotal} for p, qty, subtotal in lines],
    )


def append_order(record):
    with open(ORDERS_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def order_confirmation_text(record):
    lines_text = "\n".join("- %s x%d" % (item["name"], item["qty"]) for item in record["items"])
    return (
        "✅ Заказ оформлен (⭐ %d Stars).\n\n%s\n\nПВЗ Ozon: %s\nТелефон: %s\n\n"
        "⚠️ Напоминаем: это тестовый магазин, доставка не выполняется по-настоящему."
    ) % (record["total_stars"], lines_text, record["pvz_address"], record["phone"])


def handle_pre_checkout(token, pcq):
    items = parse_payload(pcq.get("invoice_payload", ""))
    expected_total = total_for_items(items)
    ok = bool(items) and expected_total == pcq.get("total_amount") and pcq.get("currency") == "XTR"
    log("pre_checkout_query от %s — %s" % (_who(pcq), "ok" if ok else "reject"))
    if ok:
        api(token, "answerPreCheckoutQuery", pre_checkout_query_id=pcq["id"], ok=True)
    else:
        api(
            token,
            "answerPreCheckoutQuery",
            pre_checkout_query_id=pcq["id"],
            ok=False,
            error_message="Корзина изменилась, начните оформление заново: /start",
        )


def handle_callback_query(token, query):
    data = query.get("data", "")
    user_id = query.get("from", {}).get("id")
    chat_id = (query.get("message") or {}).get("chat", {}).get("id")
    api(token, "answerCallbackQuery", callback_query_id=query["id"])
    if user_id is None or chat_id is None:
        return

    cart = carts.setdefault(user_id, {})

    if data.startswith("add:"):
        add_item(cart, int(data.split(":", 1)[1]))
        send_cart(token, chat_id, cart)
    elif data.startswith("inc:"):
        add_item(cart, int(data.split(":", 1)[1]))
        send_cart(token, chat_id, cart)
    elif data.startswith("dec:"):
        remove_item(cart, int(data.split(":", 1)[1]))
        send_cart(token, chat_id, cart)
    elif data == "cart":
        send_cart(token, chat_id, cart)
    elif data == "catalog":
        send_catalog(token, chat_id)
    elif data == "clear":
        cart.clear()
        send_cart(token, chat_id, cart)
    elif data == "checkout":
        if cart_lines(cart):
            send_invoice(token, chat_id, cart)
        else:
            send_cart(token, chat_id, cart)
    # "noop" и неизвестные data — намеренно ничего не делают


def handle_successful_payment(token, message, sp):
    user_id = message["from"]["id"]
    username = message["from"].get("username", "")
    chat_id = message["chat"]["id"]
    items = parse_payload(sp.get("invoice_payload", ""))
    paid_cart = {pid: qty for pid, qty in items}
    entry = checkout.start_checkout(paid_cart)
    checkout_state[user_id] = entry
    carts.pop(user_id, None)
    log("ОПЛАТА от %s: %s %s" % (_who(message), sp.get("total_amount"), sp.get("currency")))
    api(token, "sendMessage", chat_id=chat_id, text=ASK_ADDRESS_TEXT.format(total=entry["total"]))


def handle_checkout_text(token, message, entry):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = (message.get("text") or "").strip()
    if entry["state"] == checkout.STATE_AWAITING_ADDRESS:
        checkout.add_address(entry, text)
        if entry["state"] == checkout.STATE_AWAITING_ADDRESS:
            api(token, "sendMessage", chat_id=chat_id, text="Адрес не может быть пустым. Пришлите адрес пункта выдачи Ozon.")
        else:
            api(token, "sendMessage", chat_id=chat_id, text=ASK_PHONE_TEXT)
    elif entry["state"] == checkout.STATE_AWAITING_PHONE:
        checkout.add_phone(entry, text)
        if entry["state"] == checkout.STATE_AWAITING_PHONE:
            api(token, "sendMessage", chat_id=chat_id, text="Телефон не может быть пустым. Пришлите номер телефона, привязанный к аккаунту Ozon.")
        else:
            record = checkout.to_order_record(user_id, message["from"].get("username", ""), entry)
            append_order(record)
            del checkout_state[user_id]
            api(token, "sendMessage", chat_id=chat_id, text=order_confirmation_text(record))


def handle_update(token, update):
    if "pre_checkout_query" in update:
        handle_pre_checkout(token, update["pre_checkout_query"])
        return

    if "callback_query" in update:
        handle_callback_query(token, update["callback_query"])
        return

    message = update.get("message") or update.get("edited_message")
    if not message:
        log("пропущен апдейт без message: %s" % ", ".join(k for k in update if k != "update_id"))
        return
    chat_id = message["chat"]["id"]
    user_id = message.get("from", {}).get("id")

    if "successful_payment" in message:
        handle_successful_payment(token, message, message["successful_payment"])
        return

    text = (message.get("text") or "").strip()
    log("сообщение %r от %s" % (text[:40], _who(message)))

    if text.startswith("/help"):
        api(token, "sendMessage", chat_id=chat_id, text=HELP_TEXT)
    elif text.startswith("/paysupport"):
        api(token, "sendMessage", chat_id=chat_id, text=PAYSUPPORT_TEXT)
    elif text.startswith("/start"):
        send_start(token, chat_id)
    elif user_id in checkout_state:
        handle_checkout_text(token, message, checkout_state[user_id])
    else:
        send_start(token, chat_id)


def main():
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        sys.exit("TELEGRAM_BOT_TOKEN не задан (переменная окружения или bot/.env).")

    me = api(token, "getMe")
    if not me.get("ok"):
        sys.exit("Авторизация не удалась: %s" % me.get("description"))
    username = me["result"]["username"]

    api(
        token,
        "setMyCommands",
        commands=[
            {"command": "start", "description": "Открыть каталог"},
            {"command": "help", "description": "Что это такое"},
            {"command": "paysupport", "description": "Оплата и возвраты"},
        ],
    )

    log("Бот @%s запущен (pid %s). Long polling." % (username, os.getpid()))
    offset = None
    while True:
        try:
            params = {"timeout": 50, "allowed_updates": ["message", "callback_query", "pre_checkout_query"]}
            if offset is not None:
                params["offset"] = offset
            resp = api(token, "getUpdates", **params)
            if not resp.get("ok"):
                desc = str(resp.get("description"))
                if resp.get("error_code") == 409 or "terminated by other getUpdates" in desc:
                    log("409: запущен второй экземпляр бота. Оставь один. Пауза 10с.")
                    time.sleep(10)
                else:
                    log("getUpdates не ок: %s — пауза 3с" % desc)
                    time.sleep(3)
                continue
            for update in resp.get("result", []):
                offset = update["update_id"] + 1
                try:
                    handle_update(token, update)
                except Exception as exc:  # noqa: BLE001 — один плохой апдейт не роняет бота
                    log("[handle] ошибка: %s" % exc)
        except Exception as exc:  # noqa: BLE001 — цикл не должен падать никогда
            log("[loop] непредвиденная ошибка: %s — пауза 5с" % exc)
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nОстановлено.", flush=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.14 bots/honey-shop/tests/test_bot.py -v`
Expected: PASS (8 tests, ok)

- [ ] **Step 5: Commit**

```bash
git add bots/honey-shop/bot.py bots/honey-shop/tests/test_bot.py
git commit -m "Add honey shop bot Telegram wiring and handle_update"
```

---

### Task 5: Secrets, gitignore, README

**Files:**
- Create: `bots/honey-shop/.env.example`
- Create: `bots/honey-shop/.gitignore`
- Create: `bots/honey-shop/README.md`

**Interfaces:**
- Consumes: none (config/docs only)
- Produces: none (no code)

- [ ] **Step 1: Create `.env.example`**

```
# Скопируйте этот файл в .env и вставьте токен от @BotFather.
# Файл .env в git не попадает (см. .gitignore).
TELEGRAM_BOT_TOKEN=123456789:AA-put-your-botfather-token-here
```

- [ ] **Step 2: Create `.gitignore`**

```
.env
*.log
*.log.*
orders.jsonl
__pycache__/
*.pyc
```

- [ ] **Step 3: Create `README.md`**

```markdown
# Honey Shop Bot (тестовый магазин мёда)

Telegram-бот на чистом Python 3 stdlib. Продаёт мёд за Telegram Stars,
после оплаты собирает адрес ПВЗ Ozon и телефон для (символической)
доставки. Явно предупреждает, что это тестовый магазин.

## 1. Создать бота в BotFather

1. Откройте `@BotFather` в Telegram.
2. `/newbot` → задайте отображаемое имя (например «Медовая лавка (ТЕСТ)»)
   и уникальный `@username`, оканчивающийся на `bot`.
3. BotFather пришлёт токен вида `123456789:AA...` — скопируйте его.
4. `/mybots` → выбранный бот → `Payments` → подключите провайдера
   **Telegram Stars** (обычно уже доступен по умолчанию для XTR).

## 2. Настроить токен

```
copy .env.example .env
```

Откройте `.env` и вставьте токен из BotFather вместо плейсхолдера.

## 3. Запустить вручную (для проверки)

```
py -3.14 bot.py
```

Откройте бота в Telegram, отправьте `/start`, пройдите каталог → корзину
→ оформление заказа. Остановить — Ctrl+C.

## 4. Автозапуск (Windows Task Scheduler)

```
powershell -ExecutionPolicy Bypass -File autostart-install.ps1
```

Ставит задачу `HoneyShopBot`: старт при входе в систему, автоперезапуск
при сбое. Логи: `bot.log` (см. рядом со скриптом).

Убрать автозапуск:

```
powershell -ExecutionPolicy Bypass -File autostart-uninstall.ps1
```

## Данные заказов

Оформленные заказы дописываются построчно (JSON) в `orders.jsonl` —
этот файл не коммитится (содержит телефон и адрес).
```

- [ ] **Step 4: Commit**

```bash
git add bots/honey-shop/.env.example bots/honey-shop/.gitignore bots/honey-shop/README.md
git commit -m "Add honey shop bot config, gitignore and setup docs"
```

---

### Task 6: Autostart scripts

**Files:**
- Create: `bots/honey-shop/autostart-install.ps1`
- Create: `bots/honey-shop/autostart-uninstall.ps1`

**Interfaces:**
- Consumes: none
- Produces: none (operational scripts, not imported by any Python module)

- [ ] **Step 1: Create `autostart-install.ps1`** (adapted from `C:\Users\Андрей\Potsyk\bot\autostart-install.ps1`, task name changed to `HoneyShopBot`)

```powershell
# Автозапуск бота "Медовая лавка (тест)" через Планировщик задач Windows.
# Задача HoneyShopBot: старт при входе в систему, работа скрыто (pyw.exe),
# автоперезапуск при сбое.
#
# Запуск:  powershell -ExecutionPolicy Bypass -File autostart-install.ps1

$ErrorActionPreference = 'Stop'

$taskName = 'HoneyShopBot'
$botDir   = $PSScriptRoot
$botPy    = Join-Path $botDir 'bot.py'
$envFile  = Join-Path $botDir '.env'

if (-not (Test-Path $botPy))   { throw ('Nyet fayla: ' + $botPy) }
if (-not (Test-Path $envFile)) { throw 'Nyet .env - skopiruy .env.example v .env i vpishi token ot BotFather' }

$pyw = (Get-Command pyw.exe -ErrorAction SilentlyContinue).Source
if (-not $pyw) {
    foreach ($p in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Launcher\pyw.exe'),
        (Join-Path $env:WINDIR 'pyw.exe')
    )) { if (Test-Path $p) { $pyw = $p; break } }
}
if (-not $pyw -or -not (Test-Path $pyw)) { throw 'pyw.exe ne nayden' }

$pyver = '-3.14'
& py $pyver -c "pass" 2>$null
if ($LASTEXITCODE -ne 0) { $pyver = '-3' }

Write-Host ('pyw     : ' + $pyw)
Write-Host ('pyver   : ' + $pyver)
Write-Host ('bot.py  : ' + $botPy)

$action    = New-ScheduledTaskAction -Execute $pyw -Argument ('{0} "{1}"' -f $pyver, $botPy) -WorkingDirectory $botDir
$trigger   = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 999 -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Telegram bot honey-shop - long polling' -Force | Out-Null
} catch {
    Write-Warning ('Ne udalos sozdat zadachu: ' + $_.Exception.Message)
    Write-Host 'Zapusti PowerShell ot imeni administratora i povtori.'
    throw
}

Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*bot.py*' -and $_.CommandLine -like '*honey-shop*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 2
Start-ScheduledTask -TaskName $taskName
Start-Sleep 5

Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State | Format-Table -AutoSize
$proc = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object { $_.CommandLine -like '*bot.py*' -and $_.CommandLine -like '*honey-shop*' }
if ($proc) { Write-Host ('Bot process pid: ' + $proc.ProcessId) } else { Write-Warning 'Process bot.py ne nayden - smotri bot.log' }

Write-Host ''
Write-Host 'Gotovo. Bot startuet pri vhode v sistemu i perezapuskaetsya pri sboe.'
Write-Host ('Logi:     ' + $botDir + '\bot.log')
Write-Host 'Status:   Get-ScheduledTask HoneyShopBot'
Write-Host ('Smotret:  Get-Content "' + $botDir + '\bot.log" -Tail 20 -Wait')
Write-Host ('Ubrat:    powershell -ExecutionPolicy Bypass -File "' + $botDir + '\autostart-uninstall.ps1"')
```

- [ ] **Step 2: Create `autostart-uninstall.ps1`** (adapted from `C:\Users\Андрей\Potsyk\bot\autostart-uninstall.ps1`)

```powershell
# Убирает автозапуск бота "Медовая лавка (тест)" и останавливает работающий экземпляр.
#
# Запуск:  powershell -ExecutionPolicy Bypass -File autostart-uninstall.ps1

$ErrorActionPreference = 'Continue'
$taskName = 'HoneyShopBot'

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host ('Zadacha ' + $taskName + ' udalena.')
} else {
    Write-Host ('Zadacha ' + $taskName + ' ne naydena.')
}

Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*bot.py*' -and $_.CommandLine -like '*honey-shop*' } |
    ForEach-Object { Write-Host ('Stop pid ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force }

Write-Host 'Gotovo.'
```

- [ ] **Step 3: Commit**

```bash
git add bots/honey-shop/autostart-install.ps1 bots/honey-shop/autostart-uninstall.ps1
git commit -m "Add honey shop bot autostart scripts"
```

---

### Task 7: Manual live verification (BotFather + real Telegram client)

**Files:** none created; this task exercises Tasks 1-6 against the real Telegram Bot API.

**Interfaces:** none new.

- [ ] **Step 1: Create the bot via BotFather**

Follow `bots/honey-shop/README.md` section 1: talk to `@BotFather`,
`/newbot`, pick a display name and `@username`, copy the token, enable
the Stars payment provider under `Payments`.

- [ ] **Step 2: Fill in `.env`**

```
copy bots\honey-shop\.env.example bots\honey-shop\.env
```

Edit `bots/honey-shop/.env` and paste the real token after
`TELEGRAM_BOT_TOKEN=`.

- [ ] **Step 3: Run the bot in the foreground**

Run: `py -3.14 bots\honey-shop\bot.py`
Expected console output: `Бот @<username> запущен (pid <n>). Long polling.`

- [ ] **Step 4: Exercise the full flow from a real Telegram client**

Open the bot's `@username` in Telegram and check, in order:
1. `/start` shows the "⚠️ Это тестовый магазин..." warning and a
   "🛍 Каталог" button.
2. Tapping "Каталог" lists all 4 honey varieties with correct prices.
3. Adding two different varieties and adjusting quantity with ➖/➕
   updates the cart total shown on the "✅ Оформить заказ" button.
4. "Оформить заказ" produces a Telegram payment sheet in Stars (XTR)
   matching the cart total — do **not** complete the real payment.
5. `/help` and `/paysupport` reply with text (not silence/errors).

Watch `bots/honey-shop/bot.log` in another terminal while testing:
`Get-Content bots\honey-shop\bot.log -Tail 20 -Wait`

- [ ] **Step 5: Stop the manual run**

Press Ctrl+C in the terminal running `bot.py`.

- [ ] **Step 6: Install autostart now that manual verification passed**

```
powershell -ExecutionPolicy Bypass -File bots\honey-shop\autostart-install.ps1
```

Confirm with `Get-ScheduledTask HoneyShopBot` that the task exists and
is `Ready`/`Running`.

- [ ] **Step 7: Commit** — nothing to commit for this task (no files
  changed); record the bot's `@username` for Task 8.

---

### Task 8: Wire the bot into the site hub

**Files:**
- Modify: `js/bots.js`
- Modify: `tests/bots.test.js`

**Interfaces:**
- Consumes: `BOTS` array shape (existing, unchanged), the real bot `@username` obtained in Task 7.
- Produces: none new.

- [ ] **Step 1: Update the failing-first test to expect the new button**

```javascript
// tests/bots.test.js
const assert = require("assert");
const { BOTS } = require("../js/bots.js");

assert.strictEqual(BOTS.length, 10);

const honeyShop = BOTS[0];
assert.strictEqual(honeyShop.id, 1);
assert.strictEqual(honeyShop.title, "Магазин мёда (тест)");
assert.strictEqual(typeof honeyShop.username, "string");
assert.ok(honeyShop.username.length > 0);

BOTS.slice(1).forEach((bot, index) => {
  const expectedId = index + 2;
  assert.strictEqual(bot.id, expectedId);
  assert.strictEqual(bot.title, "Кнопка " + expectedId);
  assert.strictEqual(bot.username, null);
});

console.log("bots.test.js: OK");
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node tests/bots.test.js`
Expected: `AssertionError` — `bot.js` still has `username: null` and the
placeholder title for id 1.

- [ ] **Step 3: Update `js/bots.js`**

Replace the first entry in the `BOTS` array (the real value below
assumes the `@username` obtained in Task 7 — substitute the actual one):

```javascript
const BOTS = [
  { id: 1, title: "Магазин мёда (тест)", username: "REPLACE_WITH_REAL_BOTFATHER_USERNAME" },
  { id: 2, title: "Кнопка 2", username: null },
  { id: 3, title: "Кнопка 3", username: null },
  { id: 4, title: "Кнопка 4", username: null },
  { id: 5, title: "Кнопка 5", username: null },
  { id: 6, title: "Кнопка 6", username: null },
  { id: 7, title: "Кнопка 7", username: null },
  { id: 8, title: "Кнопка 8", username: null },
  { id: 9, title: "Кнопка 9", username: null },
  { id: 10, title: "Кнопка 10", username: null },
];

if (typeof module !== "undefined" && module.exports) {
  module.exports = { BOTS };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node tests/bots.test.js`
Expected: `bots.test.js: OK`

Also run the full existing suite to check for regressions:
Run: `node tests/render.test.js`
Expected: pass (unchanged — `buttonState` logic doesn't change).

- [ ] **Step 5: Manually verify in the browser**

Open `index.html` (or the deployed
`https://raketa4.github.io/telegram-bots-hub/`) and confirm button 1 is
now an active link to `https://t.me/<username>` and buttons 2-10 remain
disabled/"скоро".

- [ ] **Step 6: Commit and deploy**

```bash
git add js/bots.js tests/bots.test.js
git commit -m "Wire up honey shop bot button on the hub"
git push
```

GitHub Pages rebuilds automatically from `main`.

---

### Task 9: Show liter unit on products and cart quantities

**Added after live verification (Task 7):** the human partner tested the
bot against the real Bot API and asked for two display changes before
Task 8: (1) each product name should literally include its unit size
("Липовый 1 литр" instead of "Липовый"); (2) the cart should show
quantity in liters with correct Russian pluralization ("2 литра") instead
of a bare multiplier ("×2"). Pricing, catalog IDs, and all state-machine
logic are unchanged — this is a presentation-only change confined to the
product names (Task 1) and the Telegram-facing text in `bot.py` (Task 4).

**Files:**
- Modify: `bots/honey-shop/catalog.py`
- Modify: `bots/honey-shop/tests/test_catalog.py`
- Modify: `bots/honey-shop/bot.py`
- Modify: `bots/honey-shop/tests/test_bot.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `liters_text(qty: int) -> str` (in `bot.py`) — e.g. `liters_text(1) == "1 литр"`, `liters_text(2) == "2 литра"`, `liters_text(5) == "5 литров"`. Used everywhere a quantity is shown to the user (cart line, invoice description/price labels, order confirmation).

- [ ] **Step 1: Write the failing tests**

Update `bots/honey-shop/tests/test_catalog.py`'s existing `test_known_prices` and `test_get_product_found`:

```python
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
```

Add to `bots/honey-shop/tests/test_bot.py`'s `TestBotHandleUpdate` class:

```python
    def test_liters_text_pluralization(self):
        self.assertEqual(bot.liters_text(1), "1 литр")
        self.assertEqual(bot.liters_text(2), "2 литра")
        self.assertEqual(bot.liters_text(4), "4 литра")
        self.assertEqual(bot.liters_text(5), "5 литров")
        self.assertEqual(bot.liters_text(11), "11 литров")
        self.assertEqual(bot.liters_text(21), "21 литр")

    def test_cart_shows_liters_not_multiplier(self):
        bot.carts[self.USER["id"]] = {1: 2}
        update = {
            "callback_query": {
                "id": "cbq3",
                "from": self.USER,
                "data": "cart",
                "message": {"chat": {"id": self.CHAT_ID}},
            }
        }
        bot.handle_update(self.TOKEN, update)
        params = self.fake_api.last("sendMessage")
        keyboard_text = str(params["reply_markup"])
        self.assertIn("2 литра", keyboard_text)
        self.assertNotIn("×2", keyboard_text)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.14 bots/honey-shop/tests/test_catalog.py -v`
Expected: FAIL — `test_known_prices` and `test_get_product_found` assert
against names catalog.py doesn't produce yet.

Run: `py -3.14 bots/honey-shop/tests/test_bot.py -v`
Expected: FAIL — `AttributeError: module 'bot' has no attribute 'liters_text'`.

- [ ] **Step 3: Update `catalog.py`**

```python
CATALOG = [
    Product(1, "Липовый 1 литр", 60),
    Product(2, "Гречишный 1 литр", 70),
    Product(3, "Цветочный 1 литр", 55),
    Product(4, "Разнотравье 1 литр", 65),
]
```

- [ ] **Step 4: Add `liters_text` to `bot.py` and use it everywhere a quantity is shown**

Add near the top of `bot.py` (after the imports):

```python
def _liters_word(qty):
    n = abs(qty) % 100
    if 11 <= n <= 14:
        return "литров"
    last_digit = n % 10
    if last_digit == 1:
        return "литр"
    if 2 <= last_digit <= 4:
        return "литра"
    return "литров"


def liters_text(qty):
    return "%d %s" % (qty, _liters_word(qty))
```

In `cart_keyboard`, replace the multiplier-style line with a liters-based one:

```python
def cart_keyboard(cart):
    rows = []
    for product, qty, subtotal in cart_lines(cart):
        rows.append([
            {"text": "➖", "callback_data": "dec:%d" % product.id},
            {"text": "%s, %s = %d⭐" % (product.name, liters_text(qty), subtotal), "callback_data": "noop"},
            {"text": "➕", "callback_data": "inc:%d" % product.id},
        ])
    if cart:
        rows.append([{"text": "✅ Оформить заказ (%d ⭐)" % cart_total(cart), "callback_data": "checkout"}])
        rows.append([{"text": "🗑 Очистить корзину", "callback_data": "clear"}])
    rows.append([{"text": "🛍 Каталог", "callback_data": "catalog"}])
    return {"inline_keyboard": rows}
```

In `send_invoice`, replace the `"%s x%d"` formatting in both `description` and `prices`:

```python
def send_invoice(token, chat_id, cart):
    lines = cart_lines(cart)
    api(
        token,
        "sendInvoice",
        chat_id=chat_id,
        title="Заказ мёда (тест)",
        description=", ".join("%s, %s" % (p.name, liters_text(qty)) for p, qty, _ in lines),
        payload=build_payload(cart),
        currency="XTR",
        prices=[{"label": "%s, %s" % (p.name, liters_text(qty)), "amount": subtotal} for p, qty, subtotal in lines],
    )
```

In `order_confirmation_text`, replace the `"- %s x%d"` line formatting:

```python
def order_confirmation_text(record):
    lines_text = "\n".join("- %s, %s" % (item["name"], liters_text(item["qty"])) for item in record["items"])
    return (
        "✅ Заказ оформлен (⭐ %d Stars).\n\n%s\n\nПВЗ Ozon: %s\nТелефон: %s\n\n"
        "⚠️ Напоминаем: это тестовый магазин, доставка не выполняется по-настоящему."
    ) % (record["total_stars"], lines_text, record["pvz_address"], record["phone"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `py -3.14 bots/honey-shop/tests/test_catalog.py -v`
Expected: PASS (4 tests, ok)

Run: `py -3.14 bots/honey-shop/tests/test_bot.py -v`
Expected: PASS (10 tests, ok)

Run the full suite once to confirm no cross-module regressions:
`py -3.14 bots/honey-shop/tests/test_cart.py -v` and
`py -3.14 bots/honey-shop/tests/test_checkout.py -v`
Expected: both still PASS unchanged (neither references product names).

- [ ] **Step 6: Commit**

```bash
git add bots/honey-shop/catalog.py bots/honey-shop/tests/test_catalog.py bots/honey-shop/bot.py bots/honey-shop/tests/test_bot.py
git commit -m "Show liter unit on products and cart quantities"
```

---

### Task 10: Show cart contents in the message body, update in place

**Added after live re-verification of Task 9:** the human partner tested
again and reported that after adding an item twice, the order total goes
up but "nowhere is it visible that the order has 2 liters." Root cause:
the liters/quantity text only ever appeared inside a small inline-keyboard
button label, and every cart change sent a brand-new `sendMessage`
instead of updating the existing one — so the chat fills with several
near-identical "Ваша корзина:" messages and the reader may be looking at
a stale one. Fix: put the full cart contents in the message BODY TEXT
(prominent, not a small button), and edit the existing message in place
(via `editMessageText`) whenever the triggering update is a callback
query — which always carries the message being edited — instead of
sending a new message each time. Typed commands (`/start`, etc.) still
get a fresh message, since there's no existing message to edit in that
case.

**Files:**
- Modify: `bots/honey-shop/bot.py`
- Modify: `bots/honey-shop/tests/test_bot.py`

**Interfaces:**
- Consumes: nothing new (`cart_lines`, `cart_total`, `liters_text` already exist)
- Produces: `cart_summary_text(cart: dict) -> str`; `send_cart(token, chat_id, cart, message_id=None)` and `send_catalog(token, chat_id, message_id=None)` gain an optional `message_id` — when given, they call `editMessageText` instead of `sendMessage`.

- [ ] **Step 1: Write the failing tests**

Add to `bots/honey-shop/tests/test_bot.py`'s `TestBotHandleUpdate` class:

```python
    def test_cart_summary_text_shows_liters_and_total(self):
        text = bot.cart_summary_text({1: 2})  # Липовый 1 литр, qty 2, 60⭐ each
        self.assertIn("2 литра", text)
        self.assertIn("120", text)

    def test_cart_summary_text_empty_cart(self):
        text = bot.cart_summary_text({})
        self.assertIn("пуста", text.lower())

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
```

Note: `FakeApi.last(method)` (already defined in this test file) returns
`None` when no call matches — no changes needed there.

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.14 bots/honey-shop/tests/test_bot.py -v`
Expected: FAIL — `AttributeError: module 'bot' has no attribute 'cart_summary_text'` (and the message_id-based tests fail once that's fixed, since `editMessageText` is never called yet).

- [ ] **Step 3: Add `cart_summary_text` and thread `message_id` through**

Add this function in `bot.py` (near `cart_keyboard`):

```python
def cart_summary_text(cart):
    lines = cart_lines(cart)
    if not lines:
        return "Корзина пуста. Откройте каталог, чтобы что-то выбрать."
    body = "\n".join(
        "%s — %s = %d⭐" % (p.name, liters_text(qty), subtotal) for p, qty, subtotal in lines
    )
    return "Ваша корзина:\n\n%s\n\nИтого: %d ⭐" % (body, cart_total(cart))
```

Replace `send_cart` and `send_catalog`:

```python
def send_catalog(token, chat_id, message_id=None):
    text = "Выберите сорт мёда:"
    if message_id is not None:
        api(token, "editMessageText", chat_id=chat_id, message_id=message_id, text=text, reply_markup=catalog_keyboard())
    else:
        api(token, "sendMessage", chat_id=chat_id, text=text, reply_markup=catalog_keyboard())


def send_cart(token, chat_id, cart, message_id=None):
    text = cart_summary_text(cart)
    if message_id is not None:
        api(token, "editMessageText", chat_id=chat_id, message_id=message_id, text=text, reply_markup=cart_keyboard(cart))
    else:
        api(token, "sendMessage", chat_id=chat_id, text=text, reply_markup=cart_keyboard(cart))
```

Update `handle_callback_query` to extract the message id and pass it through on every branch that calls `send_cart`/`send_catalog` (the `checkout` branch's `send_invoice` call is unaffected — invoices are always a new message):

```python
def handle_callback_query(token, query):
    data = query.get("data", "")
    user_id = query.get("from", {}).get("id")
    message = query.get("message") or {}
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    api(token, "answerCallbackQuery", callback_query_id=query["id"])
    if user_id is None or chat_id is None:
        return

    cart = carts.setdefault(user_id, {})

    if data.startswith("add:"):
        add_item(cart, int(data.split(":", 1)[1]))
        send_cart(token, chat_id, cart, message_id)
    elif data.startswith("inc:"):
        add_item(cart, int(data.split(":", 1)[1]))
        send_cart(token, chat_id, cart, message_id)
    elif data.startswith("dec:"):
        remove_item(cart, int(data.split(":", 1)[1]))
        send_cart(token, chat_id, cart, message_id)
    elif data == "cart":
        send_cart(token, chat_id, cart, message_id)
    elif data == "catalog":
        send_catalog(token, chat_id, message_id)
    elif data == "clear":
        cart.clear()
        send_cart(token, chat_id, cart, message_id)
    elif data == "checkout":
        if cart_lines(cart):
            send_invoice(token, chat_id, cart)
        else:
            send_cart(token, chat_id, cart, message_id)
    # "noop" и неизвестные data — намеренно ничего не делают
```

`send_start` (used only from the `/start` text command) is unchanged — it
has no message to edit, since the user just typed a command.

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.14 bots/honey-shop/tests/test_bot.py -v`
Expected: PASS (14 tests, ok) — the 4 new tests plus all 10 previous
ones (previous tests never set `message_id` in their fixtures, so they
still exercise the `sendMessage` fallback path unchanged).

Run the other three test files to confirm no cross-module regression:
`py -3.14 bots/honey-shop/tests/test_catalog.py -v`,
`py -3.14 bots/honey-shop/tests/test_cart.py -v`,
`py -3.14 bots/honey-shop/tests/test_checkout.py -v`
Expected: all still PASS unchanged.

- [ ] **Step 5: Commit**

```bash
git add bots/honey-shop/bot.py bots/honey-shop/tests/test_bot.py
git commit -m "Show cart contents in message body; edit cart message in place"
```

---

### Task 11: Drop "1 литр" from names; merge catalog and cart into one screen

**Added after further live re-verification of Task 10:** two more
requests from the human partner. (1) Remove "1 литр" from product names
— now that quantities render via `liters_text` in the cart body (Task
10), the unit no longer needs to be baked into the name itself; plain
names read better next to a quantity like "1 литр"/"2 литра". (2) Adding
a second variety currently requires leaving the cart view and going back
to the catalog — the two screens should merge into one: every product
always shows either an "add" button (not yet in the cart) or a ➖/➕
stepper row (already in the cart), so nothing ever requires separate
"catalog" vs "cart" navigation. This removes the `catalog`/`cart`
callback actions entirely (no button will send that data anymore).

**Files:**
- Modify: `bots/honey-shop/catalog.py`
- Modify: `bots/honey-shop/tests/test_catalog.py`
- Modify: `bots/honey-shop/bot.py`
- Modify: `bots/honey-shop/tests/test_bot.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `shop_keyboard(cart: dict) -> dict`, `shop_text(cart: dict) -> str`, `send_shop(token, chat_id, cart, message_id=None)` — these REPLACE `catalog_keyboard`, `cart_keyboard`, `cart_summary_text`, `send_catalog`, `send_cart` (all four removed). `send_start(token, chat_id, cart)` gains a required `cart` parameter (was `send_start(token, chat_id)`).

- [ ] **Step 1: Write the failing tests**

Update `bots/honey-shop/tests/test_catalog.py`'s `test_known_prices` and `test_get_product_found` back to plain names:

```python
    def test_known_prices(self):
        prices = {p.name: p.price for p in CATALOG}
        self.assertEqual(
            prices,
            {"Липовый": 60, "Гречишный": 70, "Цветочный": 55, "Разнотравье": 65},
        )

    def test_get_product_found(self):
        product = get_product(1)
        self.assertEqual(product.name, "Липовый")
```

In `bots/honey-shop/tests/test_bot.py`, replace the two tests that call
the now-removed `cart_summary_text`:

```python
    def test_shop_text_shows_liters_and_total(self):
        text = bot.shop_text({1: 2})  # Липовый, qty 2, 60⭐ each
        self.assertIn("2 литра", text)
        self.assertIn("120", text)

    def test_shop_text_empty_cart(self):
        text = bot.shop_text({})
        self.assertIn("Выберите", text)
```

Replace `test_cart_shows_liters_not_multiplier` (it used the now-removed
`"cart"` callback data) with a version driven by `"add:"`, which is the
only way to reach the shop view now:

```python
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
```

Add a test proving a second variety can be added without any
catalog/cart navigation in between:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.14 bots/honey-shop/tests/test_catalog.py -v`
Expected: FAIL — names still have "1 литр".

Run: `py -3.14 bots/honey-shop/tests/test_bot.py -v`
Expected: FAIL — `AttributeError: module 'bot' has no attribute 'shop_text'`, and the callback-data tests fail since `"catalog"`/`"cart"` handling hasn't changed yet.

- [ ] **Step 3: Update `catalog.py`**

```python
CATALOG = [
    Product(1, "Липовый", 60),
    Product(2, "Гречишный", 70),
    Product(3, "Цветочный", 55),
    Product(4, "Разнотравье", 65),
]
```

- [ ] **Step 4: Replace the keyboard/view functions and callback routing in `bot.py`**

Remove `catalog_keyboard`, `cart_keyboard`, `cart_summary_text`,
`send_catalog`, `send_cart` entirely. Replace them with:

```python
def shop_keyboard(cart):
    rows = []
    for product in CATALOG:
        qty = cart.get(product.id, 0)
        if qty > 0:
            subtotal = product.price * qty
            rows.append([
                {"text": "➖", "callback_data": "dec:%d" % product.id},
                {"text": "%s, %s = %d⭐" % (product.name, liters_text(qty), subtotal), "callback_data": "noop"},
                {"text": "➕", "callback_data": "inc:%d" % product.id},
            ])
        else:
            rows.append([{"text": "%s — %d ⭐" % (product.name, product.price), "callback_data": "add:%d" % product.id}])
    if cart:
        rows.append([{"text": "✅ Оформить заказ (%d ⭐)" % cart_total(cart), "callback_data": "checkout"}])
        rows.append([{"text": "🗑 Очистить корзину", "callback_data": "clear"}])
    return {"inline_keyboard": rows}


def shop_text(cart):
    lines = cart_lines(cart)
    if not lines:
        return "Выберите сорт мёда:"
    body = "\n".join(
        "%s — %s = %d⭐" % (p.name, liters_text(qty), subtotal) for p, qty, subtotal in lines
    )
    return "Ваша корзина:\n\n%s\n\nИтого: %d ⭐" % (body, cart_total(cart))


def send_shop(token, chat_id, cart, message_id=None):
    text = shop_text(cart)
    if message_id is not None:
        api(token, "editMessageText", chat_id=chat_id, message_id=message_id, text=text, reply_markup=shop_keyboard(cart))
    else:
        api(token, "sendMessage", chat_id=chat_id, text=text, reply_markup=shop_keyboard(cart))
```

Update `send_start` to take the cart and use `shop_keyboard`:

```python
def send_start(token, chat_id, cart):
    api(token, "sendMessage", chat_id=chat_id, text=START_TEXT, reply_markup=shop_keyboard(cart))
```

Replace `handle_callback_query` (drops the `catalog`/`cart` branches,
renames the `send_cart(...)` calls to `send_shop(...)`):

```python
def handle_callback_query(token, query):
    data = query.get("data", "")
    user_id = query.get("from", {}).get("id")
    message = query.get("message") or {}
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    api(token, "answerCallbackQuery", callback_query_id=query["id"])
    if user_id is None or chat_id is None:
        return

    cart = carts.setdefault(user_id, {})

    if data.startswith("add:"):
        add_item(cart, int(data.split(":", 1)[1]))
        send_shop(token, chat_id, cart, message_id)
    elif data.startswith("inc:"):
        add_item(cart, int(data.split(":", 1)[1]))
        send_shop(token, chat_id, cart, message_id)
    elif data.startswith("dec:"):
        remove_item(cart, int(data.split(":", 1)[1]))
        send_shop(token, chat_id, cart, message_id)
    elif data == "clear":
        cart.clear()
        send_shop(token, chat_id, cart, message_id)
    elif data == "checkout":
        if cart_lines(cart):
            send_invoice(token, chat_id, cart)
        else:
            send_shop(token, chat_id, cart, message_id)
    # "noop" и неизвестные data — намеренно ничего не делают
```

Update the two call sites of `send_start` inside `handle_update` to pass
the user's cart (both are in the text-message branch, where `user_id` is
already computed as `message.get("from", {}).get("id")`):

```python
    elif text.startswith("/start"):
        send_start(token, chat_id, carts.setdefault(user_id, {}))
    elif user_id in checkout_state:
        handle_checkout_text(token, message, checkout_state[user_id])
    else:
        send_start(token, chat_id, carts.setdefault(user_id, {}))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `py -3.14 bots/honey-shop/tests/test_catalog.py -v`
Expected: PASS (4 tests, ok)

Run: `py -3.14 bots/honey-shop/tests/test_bot.py -v`
Expected: PASS (15 tests, ok) — 14 before this task, minus the 3 tests
this task replaces (`test_cart_summary_text_shows_liters_and_total`,
`test_cart_summary_text_empty_cart`, `test_cart_shows_liters_not_multiplier`),
plus their 3 renamed replacements, plus 1 new test
(`test_can_add_second_variety_directly_from_shop_view`).

Run the other two test files to confirm no regression:
`py -3.14 bots/honey-shop/tests/test_cart.py -v` and
`py -3.14 bots/honey-shop/tests/test_checkout.py -v`
Expected: both still PASS unchanged.

- [ ] **Step 6: Commit**

```bash
git add bots/honey-shop/catalog.py bots/honey-shop/tests/test_catalog.py bots/honey-shop/bot.py bots/honey-shop/tests/test_bot.py
git commit -m "Merge catalog and cart into one shop view; drop liter suffix from names"
```

---

## Self-Review Notes

- **Spec coverage:** every numbered step of "Пользовательский флоу" in
  the spec maps to a piece of `handle_update`/helpers in Task 4;
  "Каталог товаров" → Task 1; "Данные и состояние" → Tasks 2-3;
  "Команды" → Task 4 (`/start`, `/help`, `/paysupport`); "Возвраты" is
  explicitly out of scope per spec, no task implements it; "Логирование
  и хранение данных" → Task 4 (`append_order`, `.gitignore` in Task 5);
  "Деплой и автозапуск" → Task 6-7; "Хаб" → Task 8.
- **Type/name consistency:** `carts`/`checkout_state` module dicts,
  `cart.add_item`/`remove_item`/`cart_lines`/`cart_total`/
  `build_payload`/`parse_payload`/`items_from_cart`/`total_for_items`,
  and `checkout.start_checkout`/`add_address`/`add_phone`/
  `to_order_record`/`STATE_*` are named identically everywhere they are
  defined (Tasks 1-3) and consumed (Task 4/tests).
- **Known external dependency:** Task 8 needs the real `@username` from
  Task 7 (bot creation happens live in Telegram, outside this repo) —
  this is an unavoidable runtime value, not a design gap.
