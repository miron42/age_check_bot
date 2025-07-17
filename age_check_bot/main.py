import asyncio
import os
from datetime import datetime
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    filters,
)
from config import BOT_TOKEN, MEDIA_FOLDER
from db import (
    init_db,
    add_admin,
    get_scheduled_broadcasts,
    remove_scheduled_broadcast
)
from bot_handlers import (
    start,
    confirm_age,
    handle_text_buttons,
    handle_photo_with_caption
)
from admin_handlers import (
    admin_panel,
    admin_inline_handler
)
from chat_join_handler import handle_join_request
from utils import send_ad_to_user


async def process_scheduled_broadcasts(app: Application):

    while True:
        now = datetime.utcnow()
        scheduled = await get_scheduled_broadcasts()
        print(f"[Scheduler] Найдено {len(scheduled)} запланированных рассылок")

        for b_id, text, image_path, send_at in scheduled:
            try:
                send_at_dt = datetime.fromisoformat(send_at)
            except Exception as e:
                print(f"[Scheduler] ❌ Ошибка парсинга времени: {e}")
                continue

            if send_at_dt <= now:
                get_confirmed_users = app.bot_data.get("get_confirmed_users")
                if not get_confirmed_users:
                    print("❗ get_confirmed_users не найден в bot_data")
                    continue

                users = await get_confirmed_users()
                print(
                    f"[Broadcast #{b_id}] Отправка {len(users)} пользователям")

                for uid in users:
                    try:
                        await send_ad_to_user(app, uid, text, image_path)
                        print(f"[Broadcast #{b_id}] ✅ Отправлено {uid}")
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        print(f"[Broadcast #{b_id}] ⚠️ Ошибка для {uid}: {e}")

                await remove_scheduled_broadcast(b_id)
                print(f"[Broadcast #{b_id}] 🧹 Удалено из базы")

        await asyncio.sleep(10)


async def main():
    if not os.path.exists(MEDIA_FOLDER):
        os.makedirs(MEDIA_FOLDER)

    await init_db()
    await add_admin(5734739119)  # ⛳ Укажи свой ID админа

    app = Application.builder().token(BOT_TOKEN).build()

    # 👇 Установка ссылки на функцию получения подтверждённых пользователей
    app.bot_data["get_confirmed_users"] = __import__("db").get_confirmed_users

    # Команды
    app.add_handler(CommandHandler("start", start))

    # Админ панель
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_inline_handler))

    # Сообщения
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.CAPTION, handle_photo_with_caption))

    # Подтверждение возраста
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("Мне есть 18"), confirm_age))

    # Join Request
    app.add_handler(ChatJoinRequestHandler(handle_join_request))

    print("✅ Бот запущен...")

    async with app:
        # Запуск фона: проверка отложенных рассылок
        asyncio.create_task(process_scheduled_broadcasts(app))

        await app.start()
        await app.updater.start_polling()
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("🛑 Бот остановлен.")
        finally:
            await app.updater.stop()
            await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Прерывание от пользователя")
