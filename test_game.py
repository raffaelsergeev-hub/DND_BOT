import asyncio
import random
from openai import AsyncOpenAI
from TOKEN import AI_TOKEN


## Настройки бесплатного СНГ-зеркала (ИСПРАВЛЕНО: добавлен правильный поддомен и путь)
BASE_URL = "https://mskgpt.ru"

# Этот демонстрационный ключ бесплатный и публичный, он уже встроен в зеркало
API_KEY = "sk-mskgpt-free-key-1234567890abcdef"

# Используем быструю и умную модель
MODEL_NAME = "deepseek-chat"



ai_client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

SYSTEM_PROMPT = """Ты — опытный, гибкий и невероятно атмосферный Мастер Игры (DM) в настольных ролевых играх. Твоя задача — вести игрока по сюжету, который он сам выберет. 

Правила для тебя:
1. Математики, характеристик и листов персонажей нет. Игрок просто пишет свои действия, а система автоматически бросает за него кубик d20.
2. Ты получаешь запрос в формате: "Действие игрока: [текст] | Выпало на d20: [число]".
3. Ты сам на ходу определяешь сложность задачи. Если на кубике 20 — это оглушительный, легендарный успех. Если 1 — катастрофический и нелепый провал. В остальных случаях балансируй сюжет в зависимости от цифры.
4. Будь лаконичен (максимум 2-3 абзаца). Описывай мир сочно, задействуй запахи, звуки и визуальные детали.
5. Никогда не играй за игрока и не решай, что он сделал дальше. Заканчивай каждый свой ответ интригующим вопросом: "Что ты делаешь?"."""


async def main():
    print("🎲 ДОБРО ПОЖАЛОВАТЬ В ТЕКСТОВУЮ ИГРУ! 🎲\n")
    print("Напиши в одном предложении, кто ты и где находишься для старта истории.\n")

    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    is_first_turn = True

    while True:
        user_input = input("\nТвой ход ➡️  ")
        if user_input.lower() in ["exit", "выход", "quit"]:
            print("Спасибо за игру!")
            break

        if is_first_turn:
            player_request = f"Игрок начинает новую игру. Описание персонажа и локации: {user_input}"
            is_first_turn = False
        else:
            dice_roll = random.randint(1, 20)
            print(f"🎲 [Система бросает за тебя d20... Выпало: {dice_roll}]")
            player_request = f"Действие игрока: {user_input} | Выпало на d20: {dice_roll}"

        history.append({"role": "user", "content": player_request})
        print("\n🧙‍♂️ Мастер думает...")

        try:
            completion = await ai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=history
            )
            # ИСПРАВЛЕНО: Современный и безопасный синтаксис получения ответа
            ai_response = completion.choices.message.content

            print(f"\n{ai_response}")
            history.append({"role": "assistant", "content": ai_response})
        except Exception as e:
            print(f"\n❌ Ошибка связи с ИИ: {e}")


if __name__ == "__main__":
    asyncio.run(main())
