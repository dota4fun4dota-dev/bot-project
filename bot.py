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
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

async def fetch_image(client, topic):
    try:
        # Создаем задачу
        resp = await client.post("https://api.kie.ai/api/v1/jobs/createTask", 
                                 json={"model": "flux-2/pro-text-to-image", "input": {"prompt": f"Cover for presentation about {topic}"}}, 
                                 headers=HEADERS)
        data = resp.json()
        if not data or 'data' not in data: return None
        task_id = data['data']['taskId']
        
        # Ждем результат
        for _ in range(12):
            await asyncio.sleep(5)
            res = await client.get(f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}", headers=HEADERS)
            res_data = res.json()
            if res_data and res_data.get('data') and res_data['data'].get('resultJson'):
                url = json.loads(res_data['data']['resultJson'])['resultUrls'][0]
                img_res = await client.get(url)
                return img_res.content
    except Exception as e:
        logging.error(f"Image error: {e}")
    return None

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Введите тему для презентации:")

@dp.message(F.text)
async def generate(message: Message):
    topic = message.text
    msg = await message.answer("⏳ Генерирую...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # 1. Текст
        prompt = "Создай структуру презентации на 3 слайда о " + topic + ". JSON: [{'title': 'Заголовок', 'content': 'Текст'}]"
        resp = await client.post("https://api.kie.ai/gemini-3.1-pro/v1/chat/completions", 
                                 json={"messages": [{"role": "user", "content": prompt}]}, headers=HEADERS)
        
        content = resp.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip()
        data = json.loads(content)

        # 2. Картинка
        img_data = await fetch_image(client, topic)

        # 3. Сборка
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = topic
        if img_data:
            slide.shapes.add_picture(BytesIO(img_data), Inches(1), Inches(2), width=Inches(4))
            
        for item in data:
            s = prs.slides.add_slide(prs.slide_layouts[1])
            s.shapes.title.text = item['title']
            s.placeholders[1].text = item['content']
            
        prs.save("final.pptx")
        await message.answer_document(FSInputFile("final.pptx"))
        await msg.delete()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
