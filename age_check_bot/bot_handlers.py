import os
import asyncio
from telegram import (Update, ReplyKeyboardMarkup,
                      InlineKeyboardMarkup, InlineKeyboardButton,
                      ReplyKeyboardRemove)
from telegram.ext import ContextTypes
from config import CHANNEL_ID, MEDIA_FOLDER
from db import (
    add_user,
    add_admin,
    get_ad,
    get_all_ads,
    get_confirmed_users,
    is_admin as db_is_admin,
    remove_ad,
    get_preview,
    set_preview,
    add_ad_get_id,
)
from utils import send_ad_to_user

admin_states = {}


def get_main_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    buttons = [["Мне есть 18"]]
    if is_admin:
        buttons.append(["Админ панель"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = await db_is_admin(user_id)
    keyboard = get_main_keyboard(is_admin)

    preview = await get_preview()
    if preview:
        text, image_path = preview
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await update.message.reply_photo(photo=photo, caption=text)
        else:
            await update.message.reply_text(text)

    await update.message.reply_text("👋 Пожалуйста, подтвердите, что вам уже есть 18 лет:", reply_markup=keyboard)


async def confirm_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await add_user(user_id)

    is_admin = await db_is_admin(user_id)
    if is_admin:
        # Кнопка только для админа
        keyboard = ReplyKeyboardMarkup(
            [["Админ панель"]], resize_keyboard=True)
    else:
        # Удаляем клавиатуру обычным пользователям
        keyboard = ReplyKeyboardRemove()

    await update.message.reply_text("✅ Спасибо! Возраст подтверждён.", reply_markup=keyboard)

    await asyncio.sleep(3.0)

    try:
        invite = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            creates_join_request=False
        )
        await update.message.reply_text(f"📎 Вот ваша ссылка для вступления в канал:\n{invite.invite_link}")
    except Exception as e:
        print(f"Ошибка создания ссылки: {e}")
        await update.message.reply_text("⚠️ Не удалось создать ссылку. Обратитесь к администратору.")

    await asyncio.sleep(5.0)

    await update.message.reply_text(
        "⚠️ Не удаляйте бота и чат, иначе процедуру модерации придётся пройти заново."
    )


async def safe_reply(update, context, text, **kwargs):
    if update.message:
        await update.message.reply_text(text, **kwargs)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, **kwargs)


async def generate_repeated_broadcasts(update, context, state):
    from datetime import timedelta
    from db import add_scheduled_broadcast
    from telegram.constants import ParseMode

    ad_id = state.get("schedule_selected_ad")
    start_at = state.get("start_at")
    hours = state.get("repeat_every_hours")
    days = state.get("duration_days")

    if not (ad_id and start_at and hours and days):
        await safe_reply(update, context, "❗ Недостаточно данных для создания рассылки. Начните заново.")
        return

    ad = await get_ad(ad_id)
    if not ad:
        await safe_reply(update, context, "❗ Ошибка: реклама не найдена.")
        return

    ad_text, ad_image = ad[1], ad[2]
    total = (days * 24) // hours
    message = f"✅ Запланировано {total} рассылок ({hours} ч каждая):\n"

    for i in range(total):
        send_at = start_at + timedelta(hours=i * hours)
        await add_scheduled_broadcast(ad_text, ad_image, send_at.isoformat())

        local_time = send_at + timedelta(hours=3)
        message += f"#{i+1}: {local_time.strftime('%d.%m %H:%M')}\n"

    await safe_reply(update, context, message.strip(), parse_mode=ParseMode.HTML)
    admin_states.pop(update.effective_user.id, None)  # Сброс сессии


async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if text == "Мне есть 18":
        await confirm_age(update, context)
        return

    elif text == "Админ панель":
        if await db_is_admin(user_id):
            from admin_handlers import show_main_admin_panel
            await show_main_admin_panel(update, context)
            return

    state = admin_states.get(user_id)

    if isinstance(state, str):
        if state == "search_ad":
            try:
                ad_id = int(text)
                ad = await get_ad(ad_id)
                if ad:
                    _, ad_text, image_path = ad
                    if image_path:
                        with open(image_path, "rb") as photo:
                            await update.message.reply_photo(photo=photo, caption=ad_text)
                    else:
                        await update.message.reply_text(ad_text)
                else:
                    await update.message.reply_text("❗ Реклама не найдена.")
            except ValueError:
                await update.message.reply_text("⚠️ ID должен быть числом.")
            finally:
                admin_states.pop(user_id, None)

        elif state == "delete_ad":
            try:
                ad_id = int(text)
                await remove_ad(ad_id)
                await update.message.reply_text(f"🗑 Реклама с ID {ad_id} удалена.")
            except Exception as e:
                await update.message.reply_text(f"❗ Ошибка при удалении: {e}")
            finally:
                admin_states.pop(user_id, None)

        elif state == "add_admin_manual":
            try:
                new_admin_id = int(text)
                await add_admin(new_admin_id)
                await update.message.reply_text(f"✅ Пользователь {new_admin_id} добавлен в админы.")
            except ValueError:
                await update.message.reply_text("❗ ID должен быть числом.")
            finally:
                admin_states.pop(user_id, None)

    elif isinstance(state, dict):
        if state.get("awaiting_custom_days"):
            try:
                days = int(text.strip())
                if days < 1:
                    raise ValueError
                state["duration_days"] = days
                await generate_repeated_broadcasts(update, context, state)
                admin_states.pop(user_id, None)
            except ValueError:
                await update.message.reply_text("⚠️ Введите положительное целое число (например, 30)")

        elif state.get("awaiting_custom_repeat"):
            try:
                hours = int(text.strip())
                if hours < 1:
                    raise ValueError
                if isinstance(admin_states.get(user_id), dict):
                    state = admin_states[user_id]
                    state["repeat_every_hours"] = hours
                    state["awaiting_datetime"] = True
                    state.pop("awaiting_custom_repeat", None)
                await update.message.reply_text(
                    f"✅ Период {hours} ч установлен.\nТеперь введите дату и время ПЕРВОЙ рассылки в формате:\n<YYYY-MM-DD HH:MM>"
                )
            except ValueError:
                await update.message.reply_text("⚠️ Введите положительное целое число (часы).")

        elif "schedule_selected_ad" in state or "awaiting_datetime" in state:
            try:
                from datetime import datetime, timedelta
                run_at_local = datetime.strptime(
                    text.strip(), "%Y-%m-%d %H:%M")
                run_at_utc = run_at_local - timedelta(hours=3)

                state["start_at"] = run_at_utc
                state["awaiting_day_count"] = True

                keyboard = [
                    [InlineKeyboardButton(
                        "7 дней", callback_data="duration_days_7")],
                    [InlineKeyboardButton(
                        "14 дней", callback_data="duration_days_14")],
                    [InlineKeyboardButton(
                        "30 дней", callback_data="duration_days_30")],
                    [InlineKeyboardButton(
                        "✍️ Задать вручную", callback_data="duration_custom")]
                ]
                await update.message.reply_text("📆 Сколько дней повторять рассылку?",
                                                reply_markup=InlineKeyboardMarkup(keyboard))
            except ValueError:
                await update.message.reply_text("⚠️ Неверный формат. Используйте: YYYY-MM-DD HH:MM")


async def handle_photo_with_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    if not message.caption:
        await message.reply_text("ℹ️ Пришлите фото *с подписью*.")
        return

    image = message.photo[-1]
    file = await image.get_file()
    file_id = image.file_unique_id
    image_path = os.path.join(MEDIA_FOLDER, f"photo_{user_id}_{file_id}.jpg")
    await file.download_to_drive(image_path)

    state = admin_states.get(user_id)

    if state == "broadcast_new":
        ad_id = await add_ad_get_id(message.caption, image_path)
        await message.reply_text(f"✅ Реклама сохранена. ID: {ad_id}")
        admin_states.pop(user_id, None)

    elif state == "broadcast_media":
        users = await get_confirmed_users()
        for uid in users:
            await send_ad_to_user(context, uid, message.caption, image_path)
            await asyncio.sleep(0.1)
        await message.reply_text("✅ Мгновенная рассылка завершена.")
        admin_states.pop(user_id, None)

    elif state == "broadcast_test":
        await send_ad_to_user(context, user_id, message.caption, image_path)
        admin_states.pop(user_id, None)

    elif state == "preview_upload":
        await set_preview(message.caption, image_path)
        await message.reply_text("✅ Превью обновлено.")
        admin_states.pop(user_id, None)


async def show_ad_list(query, context):
    ads = await get_all_ads()
    if not ads:
        await query.edit_message_text("📭 Нет рекламы в базе.")
        return

    lines = [f"🆔 {ad_id}: {text[:30]}" for ad_id, text in ads]
    await query.edit_message_text("📃 Список рекламы:\n\n" + "\n".join(lines))
