from telegram import Update
from telegram.ext import ContextTypes
from db import is_admin


def admin_only(func):
    """
    Декоратор: разрешает выполнение только администраторам.
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if await is_admin(user_id):
            return await func(update, context)
    return wrapper
