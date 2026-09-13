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
