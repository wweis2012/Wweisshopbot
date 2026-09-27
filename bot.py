import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from catalog import PRODUCTS

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в .env")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Простая корзина в памяти: user_id -> {product_id: quantity}
carts = {}

def money(value):
    return f"{value:,.0f} ₽".replace(",", " ")

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Каталог", callback_data="catalog")
    kb.button(text="🛒 Корзина", callback_data="cart")
    kb.button(text="ℹ️ О магазине", callback_data="about")
    kb.adjust(1)
    return kb.as_markup()

def catalog_keyboard():
    kb = InlineKeyboardBuilder()
    for p in PRODUCTS:
        kb.button(text=f"{p['name']} — {money(p['price'])}", callback_data=f"product:{p['id']}")
    kb.button(text="🛒 Корзина", callback_data="cart")
    kb.adjust(1)
    return kb.as_markup()

def product_keyboard(product_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ В корзину", callback_data=f"add:{product_id}")
    kb.button(text="🛍 Каталог", callback_data="catalog")
    kb.button(text="🛒 Корзина", callback_data="cart")
    kb.adjust(1, 2)
    return kb.as_markup()

def get_product(pid):
    return next((p for p in PRODUCTS if p["id"] == pid), None)

def cart_text(user_id):
    cart = carts.get(user_id, {})
    if not cart:
        return "🛒 <b>Корзина пуста</b>"

    lines = ["🛒 <b>Ваша корзина</b>\n"]
    total = 0
    for pid, qty in cart.items():
        p = get_product(pid)
        if not p:
            continue
        subtotal = p["price"] * qty
        total += subtotal
        lines.append(f"• {p['name']} × {qty} — {money(subtotal)}")
    lines.append(f"\n<b>Итого: {money(total)}</b>")
    return "\n".join(lines)

def cart_keyboard(user_id):
    kb = InlineKeyboardBuilder()
    if carts.get(user_id):
        kb.button(text="✅ Оформить заказ", callback_data="checkout")
        kb.button(text="🗑 Очистить", callback_data="clear_cart")
    kb.button(text="🛍 Каталог", callback_data="catalog")
    kb.adjust(1)
    return kb.as_markup()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 <b>Добро пожаловать в Wweis store!</b>\n\n"
        "Выберите действие:",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "catalog")
async def catalog(call: CallbackQuery):
    await call.message.edit_text(
        "🛍 <b>Каталог товаров</b>\n\nВыберите товар:",
        reply_markup=catalog_keyboard()
    )
    await call.answer()

@dp.callback_query(F.data.startswith("product:"))
async def product(call: CallbackQuery):
    pid = call.data.split(":", 1)[1]
    p = get_product(pid)
    if not p:
        await call.answer("Товар не найден", show_alert=True)
        return
    text = (
        f"<b>{p['name']}</b>\n\n"
        f"{p['description']}\n\n"
        f"💰 <b>{money(p['price'])}</b>"
    )
    await call.message.edit_text(text, reply_markup=product_keyboard(pid))
    await call.answer()

@dp.callback_query(F.data.startswith("add:"))
async def add_to_cart(call: CallbackQuery):
    pid = call.data.split(":", 1)[1]
    if not get_product(pid):
        await call.answer("Товар не найден", show_alert=True)
        return
    carts.setdefault(call.from_user.id, {})
    carts[call.from_user.id][pid] = carts[call.from_user.id].get(pid, 0) + 1
    await call.answer("Добавлено в корзину ✅")

@dp.callback_query(F.data == "cart")
async def cart(call: CallbackQuery):
    await call.message.edit_text(
        cart_text(call.from_user.id),
        reply_markup=cart_keyboard(call.from_user.id)
    )
    await call.answer()

@dp.callback_query(F.data == "clear_cart")
async def clear_cart(call: CallbackQuery):
    carts.pop(call.from_user.id, None)
    await call.message.edit_text(
        "🛒 <b>Корзина очищена</b>",
        reply_markup=main_menu()
    )
    await call.answer()

@dp.callback_query(F.data == "about")
async def about(call: CallbackQuery):
    await call.message.edit_text(
        "ℹ️ <b>О магазине</b>\n\n"
        "Здесь можно разместить описание магазина, условия доставки, "
        "контакты и график работы.",
        reply_markup=main_menu()
    )
    await call.answer()

@dp.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery):
    user_id = call.from_user.id
    if not carts.get(user_id):
        await call.answer("Корзина пуста", show_alert=True)
        return

    text = cart_text(user_id)
    if ADMIN_CHAT_ID:
        await bot.send_message(
            int(ADMIN_CHAT_ID),
            "🔔 <b>Новый заказ</b>\n\n"
            f"Покупатель: {call.from_user.full_name}\n"
            f"Username: @{call.from_user.username or 'нет'}\n"
            f"Telegram ID: <code>{user_id}</code>\n\n{text}"
        )

    carts.pop(user_id, None)
    await call.message.edit_text(
        "✅ <b>Заказ принят!</b>\n\n"
        "Мы получили ваш заказ и свяжемся с вами для уточнения деталей.",
        reply_markup=main_menu()
    )
    await call.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
