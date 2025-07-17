import os
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from decorators import admin_only
from db import (
    add_admin,
    remove_admin,
    get_admins,
    is_admin,
    get_all_ads,
    get_scheduled_broadcasts,
    remove_scheduled_broadcast,
    remove_all_scheduled_broadcasts,
)
from bot_handlers import admin_states, generate_repeated_broadcasts


async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("❗ Введите ID пользователя: /admin_add <user_id>")
        return

    try:
        new_admin_id = int(context.args[0])
        await add_admin(new_admin_id)
        await update.message.reply_text(f"✅ Пользователь {new_admin_id} добавлен в админы.")
    except ValueError:
        await update.message.reply_text("❗ ID должен быть числом.")


async def show_main_admin_panel(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    user = getattr(update_or_query, 'effective_user', None) or getattr(
        update_or_query, 'from_user', None)

    if not user or not await is_admin(user.id):
        return

    keyboard = [
        [InlineKeyboardButton("📢 Реклама", callback_data="admin_ads")],
        [InlineKeyboardButton("👥 Админы", callback_data="admin_admins")],
        [InlineKeyboardButton("📤 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🖼 Превью", callback_data="admin_preview")]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text("⚙️ Админ-панель", reply_markup=markup)
    else:
        await update_or_query.edit_message_text("⚙️ Админ-панель", reply_markup=markup)


@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_admin_panel(update, context)


@admin_only
async def admin_inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "admin_main":
        await show_main_admin_panel(query, context)

    elif data == "admin_ads":
        keyboard = [
            [InlineKeyboardButton("➕ Добавить", callback_data="add_ad")],
            [InlineKeyboardButton("📃 Список", callback_data="list_ads")],
            [InlineKeyboardButton("🔍 Поиск", callback_data="search_ad")],
            [InlineKeyboardButton("🗑 Удалить", callback_data="delete_ad")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_main")]
        ]
        await query.edit_message_text("📢 Управление рекламой:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "list_ads":
        from bot_handlers import show_ad_list
        await show_ad_list(query, context)

    elif data == "search_ad":
        admin_states[user_id] = "search_ad"
        await query.edit_message_text("🔍 Введите ID рекламы для просмотра:")

    elif data == "delete_ad":
        admin_states[user_id] = "delete_ad"
        await query.edit_message_text("🗑 Введите ID рекламы для удаления:")

    elif data == "add_ad":
        admin_states[user_id] = "broadcast_new"
        await query.edit_message_text("📷 Пришлите фото с подписью.\n(Реклама сохранится в базе)")

    elif data == "admin_admins":
        keyboard = [
            [InlineKeyboardButton("👥 Список", callback_data="list_admins")],
            [InlineKeyboardButton("➕ Добавить", callback_data="add_admin")],
            [InlineKeyboardButton(
                "➖ Удалить", callback_data="select_remove_admin")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_main")]
        ]
        await query.edit_message_text("👥 Управление администраторами:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "list_admins":
        admins = await get_admins()
        lines = []
        for admin_id in admins:
            try:
                user = await context.bot.get_chat(admin_id)
                name = f"@{user.username}" if user.username else f"{user.full_name} ({admin_id})"
            except Exception:
                name = str(admin_id)
            lines.append(f"👤 {name}")

        text = "\n".join(lines) or "Нет администраторов."
        keyboard = [[InlineKeyboardButton(
            "⬅️ Назад", callback_data="admin_admins")]]
        await query.edit_message_text(f"👥 Администраторы:\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "add_admin":
        admin_states[user_id] = "add_admin_manual"
        await query.edit_message_text("Введите ID пользователя, которого нужно добавить в админы:")

    elif data == "select_remove_admin":
        admins = await get_admins()
        keyboard = []
        for uid in admins:
            try:
                user = await context.bot.get_chat(uid)
                label = f"@{user.username}" if user.username else f"{user.full_name} ({uid})"
            except Exception:
                label = str(uid)
            keyboard.append([InlineKeyboardButton(
                label, callback_data=f"remove_admin_{uid}")])
        keyboard.append([InlineKeyboardButton(
            "⬅️ Назад", callback_data="admin_admins")])
        await query.edit_message_text("Выберите админа для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("remove_admin_"):
        uid = int(data.split("_")[-1])
        await remove_admin(uid)
        await query.edit_message_text(f"➖ Пользователь {uid} удалён из админов.")
        await admin_inline_handler(update, context)

    elif data == "admin_broadcast":
        keyboard = [
            [InlineKeyboardButton(
                "📅 Расписание", callback_data="scheduled_list_0")],
            [InlineKeyboardButton(
                "📬 Добавить", callback_data="scheduled_add")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_main")]
        ]
        await query.edit_message_text("📤 Рассылка (планировщик):", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "scheduled_remove_all":
        keyboard = [
            [InlineKeyboardButton(
                "✅ Да, удалить всё", callback_data="scheduled_confirm_delete_all")],
            [InlineKeyboardButton(
                "❌ Нет, назад", callback_data="scheduled_list")]
        ]
        await query.edit_message_text("⚠️ Удалить все рассылки?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "scheduled_confirm_delete_all":
        await remove_all_scheduled_broadcasts()
        await query.edit_message_text("🧹 Все рассылки удалены.")

    elif data == "duration_custom":
        state = admin_states.get(user_id)
        if not state:
            await query.edit_message_text("⚠️ Сессия устарела. Начните заново.")
            return
        state["awaiting_custom_days"] = True
        await query.edit_message_text("✍️ Введите количество дней (целое число):")

    elif data.startswith("duration_days_"):
        state = admin_states.get(user_id)
        if not state:
            await query.edit_message_text("⚠️ Сессия устарела. Начните заново.")
            return
        days = int(data.split("_")[-1])
        state["duration_days"] = days
        await generate_repeated_broadcasts(update, context, state)
        admin_states.pop(user_id, None)

    elif data.startswith("repeat_every_"):
        hours = int(data.split("_")[-1])
        state = admin_states.get(user_id, {})
        state["repeat_every_hours"] = hours
        admin_states[user_id] = state
        await query.edit_message_text(
            f"🔁 Рассылка каждые {hours} ч.\n📅 Введите дату и время ПЕРВОЙ рассылки:\n<YYYY-MM-DD HH:MM>"
        )

    elif data == "repeat_custom":
        state = admin_states.get(user_id, {})
        state["awaiting_custom_repeat"] = True
        admin_states[user_id] = state
        await query.edit_message_text("✍️ Введите кастомный период в часах (например, 36)")

    elif data.startswith("schedule_ad_"):
        ad_id = int(data.split("_")[-1])
        admin_states[user_id] = {"schedule_selected_ad": ad_id}
        keyboard = [
            [InlineKeyboardButton(
                "⏱ Каждые 6 ч", callback_data="repeat_every_6")],
            [InlineKeyboardButton(
                "⏱ Каждые 12 ч", callback_data="repeat_every_12")],
            [InlineKeyboardButton(
                "⏱ Каждые 24 ч", callback_data="repeat_every_24")],
            [InlineKeyboardButton("⚙ Задать вручную",
                                  callback_data="repeat_custom")]
        ]
        await query.edit_message_text(
            f"🆔 Реклама #{ad_id}\n🔁 Как часто повторять рассылку?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "scheduled_add":
        ads = await get_all_ads()
        if not ads:
            await query.edit_message_text("📭 Нет рекламы для рассылки.")
            return
        admin_states[user_id] = "schedule_select_ad"
        keyboard = []
        for ad_id, text in ads:
            preview = text[:30].replace('\n', ' ')
            keyboard.append([InlineKeyboardButton(
                f"🆔 {ad_id}: {preview}...", callback_data=f"schedule_ad_{ad_id}")])
        keyboard.append([InlineKeyboardButton(
            "⬅️ Назад", callback_data="admin_broadcast")])
        await query.edit_message_text("📋 Выберите рекламу для рассылки:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "scheduled_list":
        scheduled = await get_scheduled_broadcasts()
        if not scheduled:
            await query.edit_message_text("📭 Нет запланированных рассылок.")
            return
        keyboard = [
            [InlineKeyboardButton(
                "🗑 Удалить все", callback_data="scheduled_remove_all")]
        ]
        text_lines = []
        for b_id, text, _, send_at in scheduled:
            short = text[:30].replace("\n", " ")
            text_lines.append(f"🆔 #{b_id} — {send_at}\n📝 {short}")
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑 Удалить #{b_id}", callback_data=f"scheduled_remove_{b_id}")
            ])
        keyboard.append([InlineKeyboardButton(
            "⬅️ Назад", callback_data="admin_broadcast")])
        await query.edit_message_text("📤 Запланированные:\n\n" + "\n\n".join(text_lines),
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("scheduled_remove_"):
        ad_id = int(data.split("_")[-1])
        await remove_scheduled_broadcast(ad_id)
        keyboard = [[InlineKeyboardButton(
            "⬅️ Назад к списку", callback_data="scheduled_list")]]
        await query.edit_message_text(f"🗑 Рассылка #{ad_id} удалена.",
                                      reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("scheduled_list"):
        page = int(data.split("_")[-1]) if "_" in data else 0
        scheduled = await get_scheduled_broadcasts()

        if not scheduled:
            await query.edit_message_text("📭 Нет запланированных рассылок.")
            return

        per_page = 10
        total_pages = (len(scheduled) + per_page - 1) // per_page
        start = page * per_page
        end = start + per_page
        items = scheduled[start:end]

        keyboard = []

        for b_id, text, image_path, send_at in items:
            short_text = text[:30].replace("\n", " ").strip()
            keyboard.append([InlineKeyboardButton(
                f"🗑 Удалить #{b_id}", callback_data=f"scheduled_remove_{b_id}"
            )])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                "◀️ Назад", callback_data=f"scheduled_list_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                "▶️ Вперёд", callback_data=f"scheduled_list_{page+1}"))

        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append([InlineKeyboardButton(
            "⬅️ Назад", callback_data="admin_broadcast")])
        keyboard.insert(0, [InlineKeyboardButton(
            "🗑 Удалить все", callback_data="scheduled_remove_all")])

        message_text = f"📤 Запланированные рассылки (стр. {page+1}/{total_pages}):\n\n"
        for b_id, text, image_path, send_at in items:
            short_text = text[:30].replace("\n", " ").strip()
            message_text += f"🆔 #{b_id} — {send_at}\n📝 {short_text}\n\n"

        await query.edit_message_text(message_text.strip(), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_preview":
        admin_states[user_id] = "preview_upload"
        await query.message.reply_text("✏️ Отправьте новое превью (фото и/или текст).")