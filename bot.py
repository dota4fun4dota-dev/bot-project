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

BOT_TOKEN = "8957490808:AAEWFUdFyV8cpYE07rxbh-q2pHjsPrUXVYg"
API_KEY = "5911714ce3ffbc56f7064a9ad0708e0c" 
CHAT_API_URL = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"
IMG_API_URL = "https://api.kie.ai/api/v1/jobs"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

async def get_image_bytes(client, prompt):
    try:
        # 1. Запуск задачи
        task = await client.post(f"{IMG_API_URL}/createTask", 
                               json={"model": "flux-2/pro-text-to-image", "input": {"prompt": prompt}}, 
                               headers={"Authorization": f"Bearer {API_KEY}"})
        task_id = task.json().get("data", {}).get("taskId")
        
        # 2. Ожидание результата (до 60 секунд)
        for _ in range(12):
            await asyncio.sleep(5)
            res = await client.get(f"{IMG_API_URL}/recordInfo?taskId={task_id}", headers={"Authorization": f"Bearer {API_KEY}"})
            data = res.json().get("data", {})
            if data and data.get("resultJson"):
                result_json = json.loads(data["resultJson"])
                url = result_json.get("resultUrls", [None])[0]
                if url:
                    img_resp = await client.get(url)
                    return BytesIO(img_resp.content)
    except Exception as e:
        logging.error(f"Ошибка получения картинки: {e}")
    return None

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! Введите тему для презентации, и я создам её для вас.")

@dp.message(F.text)
async def generate(message: Message):
    topic = message.text
    msg = await message.answer("⏳ Генерирую контент и создаю изображения...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Промпт с экранированными скобками
        prompt = f"Создай структуру из 3 слайдов на тему '{topic}'. Ответ JSON: [{{'title': 'Заголовок', 'content': 'Текст', 'img_prompt': 'описание картинки для этого слайда'}}, ...]"
        
        resp = await client.post(CHAT_API_URL, json={"messages": [{"role": "user", "content": prompt}]}, 
                               headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
        
        data = json.loads(resp.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip())

        # Создание презентации
        prs = Presentation()
        for item in data:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = item.get('title', '...')
            slide.placeholders[1].text = item.get('content', '')
            
            # Вставка картинки
            img_io = await get_image_bytes(client, item.get('img_prompt', topic))
            if img_io:
                # Вставляем картинку с проверкой
                slide.shapes.add_picture(img_io, Inches(5.5), Inches(1.5), width=Inches(3.5))
            
        prs.save("final.pptx")
        await message.answer_document(FSInputFile("final.pptx"))
        await msg.delete()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
