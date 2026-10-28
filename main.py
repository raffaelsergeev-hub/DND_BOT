import asyncio
import json
import random
from html import escape

import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from openai import AsyncOpenAI
from TOKEN import AI_TOKEN, BOT_TOKEN

# ==========================================
# НАСТРОЙКИ (КОНФИГУРАЦИЯ)
# ==========================================
TG_TOKEN = BOT_TOKEN
BASE_URL = "https://openrouter.ai/api/v1"
API_KEY = AI_TOKEN
MODEL_NAME = "meta-llama/llama-3.1-8b-instruct:free"

bot = Bot(token=TG_TOKEN, default_properties=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
ai_client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

SYSTEM_PROMPT = """Ты — опытный, гибкий и невероятно атмосферный Мастер Игры (DM) в настольных ролевых играх. Твоя задача — вести игрока по сюжету, который он сам выберет. 

Правила для тебя:
1. Математики, характеристик и листов персонажей нет. Игрок просто пишет свои действия, а система автоматически бросает за него кубик d20.
2. Ты получаешь запрос в формате: "Действие игрока: [текст] | Выпало на d20: [число]".
3. Ты сам на ходу определяешь сложность задачи. Если на кубике 20 — это оглушительный, легендарный успех. Если 1 — катастрофический и нелепый провал. В остальных случаях балансируй сюжет в зависимости от цифры.
4. Будь лаконичен (максимум 2-3 абзаца). Описывай мир сочно, задействуй запахи, звуки и визуальные детали.
5. Никогда не играй за игрока и не решай, что он сделал дальше. Заканчивай каждый свой ответ интригующим вопросом: "Что ты делаешь?"."""

DB_NAME = "rpg_game.db"


# ==========================================
# АСИНХРОННАЯ РАБОТА С БАЗОЙ ДАННЫХ
# ==========================================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                context TEXT
            )
        """)
        await db.commit()


async def get_context(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT context FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            # ИСПРАВЛЕНО: Безопасное извлечение строки из кортежа sqlite
            if row and row[0]:
                return json.loads(row[0])
            return []


async def save_context(user_id, context):
    # Храним последние 12 реплик (6 ходов диалога «запрос-ответ»)
    if len(context) > 12:
        context = context[-12:]

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, context) VALUES (?, ?)",
            (user_id, json.dumps(context, ensure_ascii=False))
        )
        await db.commit()


# ==========================================
# ВСПOMОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
def format_markdown_to_html(text: str) -> str:
    """
    Безопасно переводит базовые маркдаун-выделения нейросети (** и *) в HTML,
    предварительно экранируя опасные символы <, >, &.
    """
    text = escape(text)

    while "**" in text:
        text = text.replace("**", "<b>", 1).replace("**", "</b>", 1)

    while "*" in text:
        text = text.replace("*", "<i>", 1).replace("*", "</i>", 1)

    return text


# ==========================================
# ХЕНДЛЕРЫ TELEGRAM
# ==========================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await save_context(message.from_user.id, [])

    welcome_text = (
        "🎲 <b>Добро пожаловать в бесконечное текстовое приключение!</b>\n\n"
        "Здесь нет сложных правил и листов персонажей. Напиши в одном предложении, "
        "кто ты и где находишься (например: <i>'Я уставший детектив в киберпанк-городе, сижу в баре'</i> "
        "или <i>'Я эльф-вор, который очнулся в запертой клетке'</i>).\n\n"
        "Опиши свой старт, и игра начнется!"
    )
    await message.answer(welcome_text)


@dp.message()
async def play_turn(message: types.Message):
    if not message.text:
        return

    user_id = message.from_user.id
    user_text = message.text
    history = await get_context(user_id)

    if len(history) == 0:
        player_request = f"Игрок начинает новую игру. Вот описание его персонажа и локации: {user_text}"
        dice_msg = "🌟 <b>Игра начинается!</b>"
    else:
        dice_roll = random.randint(1, 20)
        player_request = f"Действие игрока: {user_text} | Выпало на d20: {dice_roll}"

        if dice_roll == 20:
            dice_msg = "🎲 <b>Кубик: 20! (Критический успех! 🌟)</b>"
        elif dice_roll == 1:
            dice_msg = "🎲 <b>Кубик: 1! (Критический провал! 💀)</b>"
        else:
            dice_msg = f"🎲 <b>Кубик: {dice_roll}</b>"

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    messages_to_ai = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages_to_ai.extend(history)
    messages_to_ai.append({"role": "user", "content": player_request})

    try:
        completion = await ai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages_to_ai
        )
        ai_response = completion.choices[0].message.content

        history.append({"role": "user", "content": player_request})
        history.append({"role": "assistant", "content": ai_response})
        await save_context(user_id, history)

        formatted_response = format_markdown_to_html(ai_response)

        final_answer = f"{dice_msg}\n\n{formatted_response}"
        await message.answer(final_answer)

    except Exception as e:
        error_log = escape(str(e))
        await message.answer(
            f"❌ Ошибка связи с Мастером Игры. Проверьте настройки API ключа.\n<code>Технический лог: {error_log}</code>"
        )


# ==========================================
# ЗАПУСК БОТА
# ==========================================
async def main():
    await init_db()
    print("🤖 Бот-Мастер запущен и готов генерировать приключения!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
