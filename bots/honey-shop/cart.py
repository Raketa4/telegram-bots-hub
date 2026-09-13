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
