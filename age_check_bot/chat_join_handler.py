"""📥 chat_join_handler.py — обработка join-запросов от Telegram-канала.

Этот модуль ловит ChatJoinRequest и отвечает пользователю:
1. Отправляет превью (если задано);
2. Показывает кнопку подтверждения возраста.
"""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from config import CHANNEL_ID
from db import get_preview


async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает запрос на вступление в канал, отправляя превью и клавиатуру подтверждения возраста."""
    join_request = update.chat_join_request
    user_id = join_request.from_user.id

    #Обрабатываем только нужный канал
    if join_request.chat.id != CHANNEL_ID:
        return

    # 🔹 Отправляем превью (если есть)
    preview = await get_preview()
    if preview:
        text, image_path = preview
        if image_path:
            with open(image_path, 'rb') as img:
                await context.bot.send_photo(chat_id=user_id, photo=img, caption=text)
        else:
            await context.bot.send_message(chat_id=user_id, text=text)

    # 🔹 Отправляем клавиатуру для подтверждения возраста
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Мне есть 18")]],
        resize_keyboard=True
    )
    await context.bot.send_message(
        chat_id=user_id,
        text="Подтвердите, что вам уже есть 18 лет",
        reply_markup=keyboard
    )
