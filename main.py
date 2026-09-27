import asyncio
import logging
import os
import random
import sqlite3
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# Render uchun muhim ma'lumotlar Environment Variables'dan olinadi
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", 7054481836))  # Sizning ID raqamingiz

logging.basicConfig(level=logging.INFO)

# Proxy olib tashlandi, Render to'g'ridan-to'g'ri ulanadi
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Ma'lumotlar bazasini yaratish
def init_study_db():
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " user_id INTEGER UNIQUE)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS materials (id INTEGER PRIMARY KEY"
        " AUTOINCREMENT, title TEXT, file_id TEXT, file_type TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " user_id INTEGER, task TEXT, time TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS diary (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " user_id INTEGER, note TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS words (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " text TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS musics (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " text TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS secrets (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " text TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS dates (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " user_id INTEGER, title TEXT, date TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " user_id INTEGER, title TEXT, deadline TEXT)"
    )
    conn.commit()
    conn.close()


init_study_db()


# FSM Holatlari
class AdminStates(StatesGroup):
    waiting_for_material_title = State()
    waiting_for_material_file = State()
    waiting_for_word = State()
    waiting_for_music = State()
    waiting_for_secret = State()


class UserStates(StatesGroup):
    adding_task_text = State()
    adding_task_time = State()
    chat_with_admin = State()
    waiting_for_ai_question = State()
    waiting_for_mood_text = State()
    waiting_for_diary_note = State()
    entering_diary_password = State()
    chatting_back_to_user = State()
    adding_date_title = State()
    adding_date_time = State()
    adding_goal_title = State()
    adding_goal_deadline = State()


# Admin menyusi
def get_admin_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📚 Kitob qo'shish")
    builder.button(text="🧠 Kun so'zi qo'shish")
    builder.button(text="🎵 Musiqa qo'shish")
    builder.button(text="💌 Sirli xat qo'shish")
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)


# Qizaloq uchun menyu
def get_study_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📚 PDF Kitoblar")
    builder.button(text="📝 Vazifalarim (To-Do)")
    builder.button(text="🤖 AI Fan yordamchi")
    builder.button(text="😊 Kayfiyat so'rovi")
    builder.button(text="🧠 Kun so'zi (Ingliz tili)")
    builder.button(text="⏱️ Pomodoro usuli")
    builder.button(text="🎵 Fokus Musiqalar")
    builder.button(text="💡 Motivatsiya")
    builder.button(text="🎯 Maqsadlar")
    builder.button(text="💌 Sirli xat")
    builder.button(text="📅 Muhim sanalar")
    builder.button(text="✍️ Shaxsiy kundalik")
    builder.button(text="🤍 Erjonimga yozish")
    builder.adjust(3, 3, 3, 3, 1)
    return builder.as_markup(resize_keyboard=True)


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        await message.answer(
            "Salom Erjon! Boshqaruv paneli: 🚀", reply_markup=get_admin_menu()
        )
    else:
        conn = sqlite3.connect("study_bot.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
        await message.answer(
            "Salom, mening erkatoy va aqlli malikam! 🤍✨\nBarcha bo'limlar"
            " tayyor, tanla:",
            reply_markup=get_study_menu(),
        )


# --- OPENROUTER AI ---
async def ask_openrouter(prompt: str, system_prompt: str = None) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    if not system_prompt:
        system_prompt = (
            "Siz juda mehribon, erkalatib gapiradigan va shirinso'z"
            " yordamchisiz."
        )

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    }

    try:
        async with aiohttp.ClientSession() as session_ai:
            async with session_ai.post(
                url, json=payload, headers=headers, timeout=30
            ) as response:
                if response.status == 200:
                    res_json = await response.json()
                    return res_json["choices"][0]["message"]["content"]
                else:
                    return "AI bilan bog'lanishda xatolik yuz berdi."
    except Exception as e:
        return f"Xatolik: {str(e)}"


# --- ADMIN QO'SHISH BO'LIMLARI ---
@dp.message(F.text == "📚 Kitob qo'shish")
async def add_kitob(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Kitob nomini yuboring:")
    await state.set_state(AdminStates.waiting_for_material_title)


@dp.message(AdminStates.waiting_for_material_title)
async def get_k_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Endi PDF faylni yuboring:")
    await state.set_state(AdminStates.waiting_for_material_file)


@dp.message(AdminStates.waiting_for_material_file)
async def get_k_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data.get("title")
    if not message.document:
        await message.answer("Iltimos, PDF hujjat yuboring!")
        return

    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO materials (title, file_id, file_type) VALUES (?, ?, ?)",
        (title, message.document.file_id, "document"),
    )
    conn.commit()
    conn.close()
    await message.answer(
        "✅ Kitob muvaffaqiyatli qo'shildi!", reply_markup=get_admin_menu()
    )
    await state.clear()


@dp.message(F.text == "🧠 Kun so'zi qo'shish")
async def add_w_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Yangi kun so'zi va tarjimasini yuboring:")
    await state.set_state(AdminStates.waiting_for_word)


@dp.message(AdminStates.waiting_for_word)
async def save_w(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO words (text) VALUES (?)", (message.text,))
    conn.commit()
    conn.close()
    await message.answer("✅ Kun so'zi saqlandi!", reply_markup=get_admin_menu())
    await state.clear()


@dp.message(F.text == "🎵 Musiqa qo'shish")
async def add_mus_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Musiqa nomi va havolasini yuboring:")
    await state.set_state(AdminStates.waiting_for_music)


@dp.message(AdminStates.waiting_for_music)
async def save_mus(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO musics (text) VALUES (?)", (message.text,))
    conn.commit()
    conn.close()
    await message.answer("✅ Musiqa qo'shildi!", reply_markup=get_admin_menu())
    await state.clear()


@dp.message(F.text == "💌 Sirli xat qo'shish")
async def add_sec_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Yangi sirli xat matnini yuboring:")
    await state.set_state(AdminStates.waiting_for_secret)


@dp.message(AdminStates.waiting_for_secret)
async def save_sec(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO secrets (text) VALUES (?)", (message.text,))
    conn.commit()
    conn.close()
    await message.answer(
        "✅ Sirli xat qo'shildi!", reply_markup=get_admin_menu()
    )
    await state.clear()


# --- 13 TA FUNKSIYA ---

# 1. PDF Kitoblar
@dp.message(F.text == "📚 PDF Kitoblar")
async def show_kitoblar(message: types.Message):
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM materials")
    items = cursor.fetchall()
    conn.close()
    if not items:
        await message.answer("Hozircha kitoblar yo'q 📚")
        return
    builder = InlineKeyboardBuilder()
    for m in items:
        builder.button(text=f"📖 {m[1]}", callback_data=f"kitob_{m[0]}")
    builder.adjust(1)
    await message.answer(
        "Sening elektron kitoblaring:", reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data.startswith("kitob_"))
async def send_kitob_file(callback: types.CallbackQuery):
    mat_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title, file_id FROM materials WHERE id = ?", (mat_id,))
    mat = cursor.fetchone()
    conn.close()
    if mat:
        await callback.message.answer_document(
            document=mat[1], caption=f"📖 {mat[0]}"
        )
    await callback.answer()


# 2. Vazifalarim (To-Do)
@dp.message(F.text == "📝 Vazifalarim (To-Do)")
async def todo_menu(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, task, time FROM tasks WHERE user_id = ?", (user_id,))
    tasks = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.button(
            text=f"✅ {t[1]} ({t[2]}) - Bajarildi", callback_data=f"deltask_{t[0]}"
        )
    builder.button(text="➕ Yangi vazifa qo'shish", callback_data="add_task")
    builder.adjust(1)

    text = (
        "📝 **Sening vazifalaring va eslatma vaqtlaring:**\n\n"
        + (
            "\n".join([f"• {t[1]} ⏰ *{t[2]}*" for t in tasks])
            if tasks
            else "Hozircha vazifalar yo'q. Istasang pastdagi tugmani bosib yangi vazifa qo'sh!"
        )
    )
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@dp.callback_query(F.data == "add_task")
async def ask_task(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "✍️ Yangi vazifa nomini yozing (masalan: Matematika darsini qilish):"
    )
    await state.set_state(UserStates.adding_task_text)
    await callback.answer()


@dp.message(UserStates.adding_task_text)
async def get_t_text(message: types.Message, state: FSMContext):
    await state.update_data(task=message.text)
    await message.answer(
        "⏰ Endi aniq vaqtni yozing (Masalan: 19:30 formatida):"
    )
    await state.set_state(UserStates.adding_task_time)


@dp.message(UserStates.adding_task_time)
async def get_t_time(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_text = data.get("task")
    task_time = message.text
    user_id = message.from_user.id

    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (user_id, task, time) VALUES (?, ?, ?)",
        (user_id, task_text, task_time),
    )
    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Vazifa saqlandi! {task_time} da eslatib turaman, malikam! 🤍",
        reply_markup=get_study_menu(),
    )
    await state.clear()


@dp.callback_query(F.data.startswith("deltask_"))
async def del_task(callback: types.CallbackQuery):
    task_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    await callback.message.answer(
        "🎉 Barakalla! Vazifa bajarildi deb belgilandi va o'chirildi!"
    )
    await callback.answer()


# 3. AI Fan yordamchi
@dp.message(F.text == "🤖 AI Fan yordamchi")
async def ai_start(message: types.Message, state: FSMContext):
    await message.answer(
        "🤖 Jonim, qaysi fandan qiynalyapsan? Menga yoz, hammasini"
        " tushuntirib beraman! ✨"
    )
    await state.set_state(UserStates.waiting_for_ai_question)


@dp.message(UserStates.waiting_for_ai_question)
async def ai_answer(message: types.Message, state: FSMContext):
    wait = await message.answer(
        "🤔 O'ylayapman, jonim, bir zum kut..."
    )
    system_p = (
        "Siz juda mehribon, o'quvchini qattiq yaxshi ko'radigan, har doim"
        " erkalatib, 'jonim', 'malikam' deb murojaat qiladigan va fanlarni"
        " tushuntirib beradigan aqlli ustozsiz."
    )
    ans = await ask_openrouter(message.text, system_prompt=system_p)
    await bot.delete_message(chat_id=message.chat.id, message_id=wait.message_id)
    await message.answer(f"🤖 **AI Yordamchi:**\n\n{ans}", parse_mode="Markdown")
    await state.clear()


# 4. Kayfiyat so'rovi
@dp.message(F.text == "😊 Kayfiyat so'rovi")
async def mood_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="😄 Quvnoq / Zo'r", callback_data="mood_happy")
    builder.button(text="😡 Jahldor / G'azablangan", callback_data="mood_angry")
    builder.button(text="😢 Xafa / G'amgin", callback_data="mood_sad")
    builder.button(text="❓ Aniq bilmayman", callback_data="mood_unknown")
    builder.adjust(1)
    await message.answer(
        "😊 Hozir kayfiyating qanday, jonim? Tanla:",
        reply_markup=builder.as_markup(),
    )


@dp.callback_query(F.data.startswith("mood_"))
async def mood_selected(callback: types.CallbackQuery, state: FSMContext):
    mood_type = callback.data.split("_")[1]
    mood_names = {
        "happy": "Quvnoq / Zo'r",
        "angry": "Jahldor / G'azablangan",
        "sad": "Xafa / G'amgin",
        "unknown": "Aniq bilmayman",
    }
    selected_name = mood_names.get(mood_type, "Noma'lum")

    await state.update_data(mood_name=selected_name)
    await callback.message.answer(
        f"Sizning kayfiyatingiz: *{selected_name}*.\nNega bunday his"
        " qilyapsan, sababini yozib yubor, jonim:"
    )
    await state.set_state(UserStates.waiting_for_mood_text)
    await callback.answer()


@dp.message(UserStates.waiting_for_mood_text)
async def process_mood_reason(message: types.Message, state: FSMContext):
    data = await state.get_data()
    mood_name = data.get("mood_name", "Bilinmadi")
    reason = message.text
    user_name = message.from_user.first_name

    wait = await message.answer("🤍 Senga erkalovchi javob tayyorlayapman...")

    system_p = (
        "Siz qizaloqning eng yaqin, mehr bilan erkalatuvchi do'stisiz. U o'z"
        " kayfiyati va sababini yozdi. Unga iliq dalda bering, xafa bo'lsa"
        " ko'nglini ko'taring."
    )
    ai_reply = await ask_openrouter(
        f"Mening kayfiyatim: {mood_name}. Sababi: {reason}",
        system_prompt=system_p,
    )

    await bot.delete_message(
        chat_id=message.chat.id, message_id=wait.message_id
    )
    await message.answer(ai_reply, reply_markup=get_study_menu())

    # Adminga xabar yuborish
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🚨 **Qizingizning kayfiyati haqida xabar!**\n\nKim:"
                f" {user_name}\nKayfiyati: *{mood_name}*\nSababi: {reason}"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logging.error(f"Adminga xabar yuborishda xatolik: {e}")

    await state.clear()


# 5. Kun so'zi
@dp.message(F.text == "🧠 Kun so'zi (Ingliz tili)")
async def show_word(message: types.Message):
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT text FROM words")
    words = cursor.fetchall()
    conn.close()
    if not words:
        await message.answer("Hozircha kun so'zlari qo'shilmagan.")
        return
    await message.answer(
        f"🧠 **Bugungi inglizcha so'z:**\n\n{random.choice(words)[0]}",
        parse_mode="Markdown",
    )


# 6. Pomodoro usuli
@dp.message(F.text == "⏱️ Pomodoro usuli")
async def pomodoro_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🍅 25 daqiqa dars", callback_data="pomo_25")
    builder.button(text="☕ 5 daqiqa dam olish", callback_data="pomo_5")
    builder.button(text="📚 1 soat dars", callback_data="pomo_60")
    builder.adjust(1)
    await message.answer(
        "⏱️ **Pomodoro rejimini tanla, jonim:**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )


@dp.callback_query(F.data.startswith("pomo_"))
async def start_pomodoro_timer(callback: types.CallbackQuery):
    action = callback.data.split("_")[1]
    if action == "25":
        minutes = 25
        text = "25 daqiqalik dars vaqti boshlandi! Diqqatni jamla, men sendaman! 🍅"
    elif action == "5":
        minutes = 5
        text = (
            "5 daqiqalik dam olish boshlandi! Choy ichib biroz hordiq chiqar. ☕"
        )
    else:
        minutes = 60
        text = "1 soatlik kuchli dars vaqti boshlandi! Omad, malikam! 📚"

    await callback.message.answer(
        f"⏳ **{minutes} daqiqalik taymer ishga tushdi!**\n{text}"
    )
    await callback.answer()

    asyncio.create_task(
        pomodoro_alarm(callback.message.chat.id, minutes, action)
    )


async def pomodoro_alarm(chat_id: int, minutes: int, action: str):
    await asyncio.sleep(minutes * 60)
    if action == "5":
        msg = "☕ **Vaqt tugadi, jonim!** Dam olish vaqti tugatildi, endi yana darsga qaytamiz!"
    else:
        msg = f"⏰ **{minutes} daqiqalik vaqt tugadi!** Juda zo'r ishlading, endi biroz dam ol, malikam! ✨"
    await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")


# 7. Fokus Musiqalar
@dp.message(F.text == "🎵 Fokus Musiqalar")
async def show_musics(message: types.Message):
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT text FROM musics")
    items = cursor.fetchall()
    conn.close()
    if not items:
        await message.answer("Hozircha musiqalar qo'shilmagan.")
        return
    text = "\n\n".join([m[0] for m in items])
    await message.answer(
        f"🎵 **Fokus musiqalar ro'yxati:**\n\n{text}",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


# 8. Motivatsiya
@dp.message(F.text == "💡 Motivatsiya")
async def give_motivation(message: types.Message):
    wait = await message.answer("💡 Senga maxsus motivatsiya tayyorlayapman...")
    prompt = "Siz sevgan qizaloqqa juda shirin, erkalatib, uni ruhlantiradigan va motivatsiya beradigan so'zlar yozing."
    ans = await ask_openrouter(
        prompt,
        system_prompt=(
            "Siz juda mehribon va g'amxo'r do'stsiz, qizaloqqa sevgi va ishonch"
            " bilan motivatsiya bering."
        ),
    )
    await bot.delete_message(chat_id=message.chat.id, message_id=wait.message_id)
    await message.answer(
        f"💡 **Sening uchun:**\n\n{ans}", parse_mode="Markdown"
    )


# 9. Maqsadlar
@dp.message(F.text == "🎯 Maqsadlar")
async def goals_menu(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT title, deadline FROM goals WHERE user_id = ?", (user_id,)
    )
    goals = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi maqsad qo'shish", callback_data="add_goal")
    builder.adjust(1)

    text = (
        "🎯 **Sening oldinga qo'ygan maqsadlaring:**\n\n"
        + (
            "\n".join([f"• {g[0]} (Muddat: *{g[1]}*)" for g in goals])
            if goals
            else "Hozircha maqsadlar kiritilmagan."
        )
    )
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@dp.callback_query(F.data == "add_goal")
async def ask_goal(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Maqsad nomini yozing (masalan: Ingliz tilidan B2 olish):"
    )
    await state.set_state(UserStates.adding_goal_title)
    await callback.answer()


@dp.message(UserStates.adding_goal_title)
async def get_g_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Shu maqsadga erishish muddatini yozing (masalan: 2026-yil oxiri):")
    await state.set_state(UserStates.adding_goal_deadline)


@dp.message(UserStates.adding_goal_deadline)
async def get_g_deadline(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data.get("title")
    deadline = message.text
    user_id = message.from_user.id

    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO goals (user_id, title, deadline) VALUES (?, ?, ?)",
        (user_id, title, deadline),
    )
    conn.commit()
    conn.close()

    await message.answer(
        "✅ Maqsad qo'shildi! Sen albatta bunga erishasan, malikam! 🤍",
        reply_markup=get_study_menu(),
    )
    await state.clear()


# 10. Sirli xat
@dp.message(F.text == "💌 Sirli xat")
async def show_secrets(message: types.Message):
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT text FROM secrets")
    items = cursor.fetchall()
    conn.close()
    if not items:
        await message.answer("Hozircha sirli xatlar qo'shilmagan.")
        return
    await message.answer(
        f"💌 **Sirli xat:**\n\n{random.choice(items)[0]}", parse_mode="Markdown"
    )


# 11. Muhim sanalar
@dp.message(F.text == "📅 Muhim sanalar")
async def dates_menu(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT title, date FROM dates WHERE user_id = ?", (user_id,)
    )
    items = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Muhim sana qo'shish", callback_data="add_date")
    builder.adjust(1)

    text = (
        "📅 **Muhim sanalaring va eslatmalar:**\n\n"
        + (
            "\n".join([f"• {d[0]} — *{d[1]}*" for d in items])
            if items
            else "Hozircha muhim sanalar yo'q."
        )
    )
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@dp.callback_query(F.data == "add_date")
async def ask_date(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Muhim sana nomini yozing (masalan: Imtihon kuni):"
    )
    await state.set_state(UserStates.adding_date_title)
    await callback.answer()


@dp.message(UserStates.adding_date_title)
async def get_d_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Sanani yozing (masalan: 15-aprel):")
    await state.set_state(UserStates.adding_date_time)


@dp.message(UserStates.adding_date_time)
async def get_d_time(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data.get("title")
    date_str = message.text
    user_id = message.from_user.id

    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO dates (user_id, title, date) VALUES (?, ?, ?)",
        (user_id, title, date_str),
    )
    conn.commit()
    conn.close()

    await message.answer(
        "✅ Muhim sana saqlandi!", reply_markup=get_study_menu()
    )
    await state.clear()


# 12. Shaxsiy kundalik (Parol: 1820)
@dp.message(F.text == "✍️ Shaxsiy kundalik")
async def diary_auth(message: types.Message, state: FSMContext):
    await message.answer(
        "🔐 Shaxsiy kundaligingizni ochish uchun maxfiy parolni kiriting:"
    )
    await state.set_state(UserStates.entering_diary_password)


@dp.message(UserStates.entering_diary_password)
async def check_diary_password(message: types.Message, state: FSMContext):
    if message.text == "1820":
        user_id = message.from_user.id
        conn = sqlite3.connect("study_bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT note FROM diary WHERE user_id = ?", (user_id,))
        notes = cursor.fetchall()
        conn.close()

        notes_text = (
            "\n".join([f"• {n[0]}" for n in notes])
            if notes
            else "Kundaligingiz hozircha bo'sh."
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="✍️ Yangi eslatma yozish", callback_data="add_diary")
        builder.adjust(1)

        await message.answer(
            f"🔓 Parol to'g'ri! Sening shaxsiy kundaliging:\n\n{notes_text}",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )
        await state.clear()
    else:
        await message.answer("❌ Parol noto'g'ri! Qaytadan urinib ko'ring:")


@dp.callback_query(F.data == "add_diary")
async def ask_diary_note(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Kundalikka nima yozmoqchisan, jonim?")
    await state.set_state(UserStates.waiting_for_diary_note)
    await callback.answer()


@dp.message(UserStates.waiting_for_diary_note)
async def save_diary_note(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = sqlite3.connect("study_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO diary (user_id, note) VALUES (?, ?)",
        (user_id, message.text),
    )
    conn.commit()
    conn.close()
    await message.answer(
        "✅ Kundalikka xavfsiz saqlandi, malikam! 🤍",
        reply_markup=get_study_menu(),
    )
    await state.clear()


# 13. Erjonimga yozish
@dp.message(F.text == "🤍 Erjonimga yozish")
async def chat_admin(message: types.Message, state: FSMContext):
    await message.answer(
        "Erjoningizga yubormoqchi bo'lgan xabaringizni yozing, tezda"
        " yetkazaman:"
    )
    await state.set_state(UserStates.chat_with_admin)


@dp.message(UserStates.chat_with_admin)
async def send_to_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Javob berish", callback_data=f"replyto_{user_id}")

    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📩 **Sevgan qizingizdan xabar ({user_name}):**\n\n{message.text}"
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )
        await message.answer(
            "✅ Xabaringiz Erjoningizga yetkazildi! 🤍",
            reply_markup=get_study_menu(),
        )
    except Exception as e:
        await message.answer(
            "❌ Xabarni Adminga yetkazishda xatolik yuz berdi. (Admin botni"
            f" bloklagan yoki boshlamagan bo'lishi mumkin): {e}"
        )
    
    await state.clear()


# Admin qizaloqning xabariga javob berishi uchun
@dp.callback_query(F.data.startswith("replyto_"))
async def admin_reply_start(callback: types.CallbackQuery, state: FSMContext):
    target_user_id = int(callback.data.split("_")[1])
    await state.update_data(target_user_id=target_user_id)
    await callback.message.answer(
        "Qizingizga yubormoqchi bo'lgan javobingizni yozing:"
    )
    await state.set_state(UserStates.chatting_back_to_user)
    await callback.answer()


@dp.message(UserStates.chatting_back_to_user)
async def admin_send_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=f"🤍 **Erjoningizdan javob:**\n\n{message.text}",
            parse_mode="Markdown",
        )
        await message.answer("✅ Javobingiz muvaffaqiyatli yuborildi!")
    except Exception as e:
        await message.answer(f"Xatolik yuborishda: {e}")
    await state.clear()


async def main():
    print("Bot Render uchun muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())