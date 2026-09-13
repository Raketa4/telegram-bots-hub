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
    entry["address"] = text.strip()
    entry["state"] = STATE_AWAITING_PHONE
    return entry


def add_phone(entry, text):
    entry["phone"] = text.strip()
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
