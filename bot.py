import asyncio
import logging
import httpx
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from pptx import Presentation
from pptx.util import Inches
from io import BytesIO

# Настройки
BOT_TOKEN = "8957490808:AAEWFUdFyV8cpYE07rxbh-q2pHjsPrUXVYg"
API_KEY = "5911714ce3ffbc56f7064a9ad0708e0c" 
CHAT_API_URL = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def start(message: Message):
    # Никаких проверок подписки, только приветствие
    await message.answer("Привет! Я бот для создания презентаций. Напиши тему, и я создам файл.")

@dp.message(F.text)
async def create_presentation(message: Message):
    topic = message.text
    msg = await message.answer("⏳ Генерирую презентацию...")
    
    # Запрос к ИИ
    prompt = f"Создай структуру из 3 слайдов на тему '{topic}'. Ответ JSON: [{'title': 'Заголовок', 'content': 'Текст'}, ...]"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(CHAT_API_URL, json={"messages": [{"role": "user", "content": prompt}]}, 
                                   headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
            
            # Очистка от markdown
            content = resp.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip()
            data = json.loads(content)

            # Создание PPTX
            prs = Presentation()
            for item in data:
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = item.get('title', '...')
                slide.placeholders[1].text = item.get('content', '')
            
            filename = "presentation.pptx"
            prs.save(filename)
            
            await message.answer_document(FSInputFile(filename))
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"Ошибка: {str(e)}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
