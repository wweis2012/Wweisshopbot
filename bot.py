import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from catalog import PRODUCTS

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip().lstrip("@")

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в Railway Variables")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Корзины хранятся в памяти: user_id -> {product_id: quantity}
carts = {}


def money(value):
    return f"{value:,.0f} ₽".replace(",", " ")


def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Товары", callback_data="catalog")
    kb.button(text="⭐ Отзывы", callback_data="reviews")
    kb.button(text="🆘 Поддержка", callback_data="support")
    kb.button(text="📖 Инструкция", callback_data="instruction")
    kb.button(text="🛒 Корзина", callback_data="cart")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def back_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Главное меню", callback_data="home")
    return kb.as_markup()


def catalog_keyboard():
    kb = InlineKeyboardBuilder()

    for p in PRODUCTS:
        kb.button(
            text=f"{p['name']} — {money(p['price'])}",
            callback_data=f"product:{p['id']}"
        )

    kb.button(text="🛒 Корзина", callback_data="cart")
    kb.button(text="🏠 Главное меню", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def product_keyboard(product_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ В корзину", callback_data=f"add:{product_id}")
    kb.button(text="🛍 Товары", callback_data="catalog")
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

    kb.button(text="🛍 Товары", callback_data="catalog")
    kb.button(text="🏠 Главное меню", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎮 <b>Добро пожаловать в Wweis store!</b> 🎮\n\n"
        "🔥 Здесь ты можешь приобрести товары для Brawl Stars!\n\n"
        "🛒 Выбирай нужный товар в каталоге и оформляй заказ прямо в боте.\n\n"
        "⚡ Быстро • Удобно • Просто\n\n"
        "👇 <b>Выбери действие в меню ниже:</b>",
        reply_markup=main_menu()
    )


@dp.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(
        f"🆔 Твой Telegram ID:\n<code>{message.from_user.id}</code>\n\n"
        "Этот номер можно указать в Railway → Variables → ADMIN_CHAT_ID."
    )


@dp.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    await call.message.edit_text(
        "🎮 <b>Wweis store</b>\n\n"
        "Выбери нужный раздел ниже:",
        reply_markup=main_menu()
    )
    await call.answer()


@dp.callback_query(F.data == "catalog")
async def catalog(call: CallbackQuery):
    await call.message.edit_text(
        "🛍 <b>Товары</b>\n\nВыберите товар:",
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
        "🗑 <b>Корзина очищена.</b>\n\n"
        "Можно выбрать товары заново.",
        reply_markup=main_menu()
    )
    await call.answer()


@dp.callback_query(F.data == "about")
async def about(call: CallbackQuery):
    await call.message.edit_text(
        "ℹ️ <b>О магазине</b>\n\n"
        "🎮 <b>Wweis store</b>\n\n"
        "Здесь можно приобрести товары для Brawl Stars.\n\n"
        "📦 После оформления заказа заявка поступит администратору.\n"
        "💬 По вопросам заказа обращайтесь в поддержку.",
        reply_markup=back_menu()
    )
    await call.answer()


@dp.callback_query(F.data == "reviews")
async def reviews(call: CallbackQuery):
    await call.message.edit_text(
        "⭐ <b>Отзывы</b>\n\n"
        "Здесь будут размещаться отзывы покупателей.\n\n"
        "📝 Раздел можно заполнить после первых заказов.",
        reply_markup=back_menu()
    )
    await call.answer()


@dp.callback_query(F.data == "support")
async def support(call: CallbackQuery):
    if SUPPORT_USERNAME:
        text = (
            "🆘 <b>Поддержка</b>\n\n"
            "Если у тебя есть вопрос по заказу, напиши администратору:\n"
            f"👉 @{SUPPORT_USERNAME}"
        )
    else:
        text = (
            "🆘 <b>Поддержка</b>\n\n"
            "По вопросам заказа обратитесь к администратору.\n\n"
            "Администратор может добавить свой Telegram-username "
            "через переменную SUPPORT_USERNAME в Railway."
        )

    await call.message.edit_text(text, reply_markup=back_menu())
    await call.answer()


@dp.callback_query(F.data == "instruction")
async def instruction(call: CallbackQuery):
    await call.message.edit_text(
        "📖 <b>Инструкция</b>\n\n"
        "1️⃣ Открой раздел «Товары».\n"
        "2️⃣ Выбери нужный товар.\n"
        "3️⃣ Нажми «В корзину».\n"
        "4️⃣ Открой «Корзину».\n"
        "5️⃣ Нажми «Оформить заказ».\n\n"
        "✅ После оформления информация о заказе отправится администратору.",
        reply_markup=back_menu()
    )
    await call.answer()


@dp.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery):
    user_id = call.from_user.id
    cart = carts.get(user_id, {})

    if not cart:
        await call.answer("Корзина пуста", show_alert=True)
        return

    order_text = cart_text(user_id)

    # Сначала подтверждаем нажатие кнопки, чтобы Telegram
    # не показывал бесконечную загрузку.
    await call.answer("Оформляем заказ…")

    if not ADMIN_CHAT_ID:
        await call.message.edit_text(
            "⚠️ <b>Заказ не отправлен администратору.</b>\n\n"
            "Администратор ещё не настроил ADMIN_CHAT_ID в Railway.",
            reply_markup=main_menu()
        )
        return

    try:
        admin_id = int(ADMIN_CHAT_ID)

        await bot.send_message(
            admin_id,
            "🔔 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
            f"👤 Покупатель: {call.from_user.full_name}\n"
            f"📱 Username: @{call.from_user.username or 'нет'}\n"
            f"🆔 Telegram ID: <code>{user_id}</code>\n\n"
            f"{order_text}"
        )

        carts.pop(user_id, None)

        await call.message.edit_text(
            "✅ <b>Заказ принят!</b>\n\n"
            "Информация о заказе отправлена администратору.\n"
            "Ожидайте сообщения для уточнения деталей.",
            reply_markup=main_menu()
        )

    except Exception:
        await call.message.edit_text(
            "⚠️ <b>Не удалось отправить заказ.</b>\n\n"
            "Попробуйте ещё раз немного позже.",
            reply_markup=main_menu()
        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())