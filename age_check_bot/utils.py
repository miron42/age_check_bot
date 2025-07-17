"""📦 utils.py — утильные функции для Telegram-бота."""

import os
from telegram.ext import ContextTypes


async def send_ad_to_user(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    text: str,
    image_path: str | None
) -> None:
    """
    Универсальная отправка рекламного сообщения пользователю.

    Если передан путь к изображению и файл существует — отправляется фото с подписью.
    В противном случае — обычное текстовое сообщение.

    :param context: Контекст бота от PTB
    :param user_id: Telegram ID получателя
    :param text: Текст рекламы
    :param image_path: Путь до изображения (или None)
    """
    try:
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await context.bot.send_photo(chat_id=user_id, photo=photo, caption=text)
        else:
            await context.bot.send_message(chat_id=user_id, text=text)
    except Exception as e:
        print(
            f"[send_ad_to_user] ❌ Ошибка при отправке пользователю {user_id}: {e}")
