import asyncio
import logging
import requests
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from pptx import Presentation
from pptx.util import Inches
from io import BytesIO

BOT_TOKEN = "8957490808:AAEWFUdFyV8cpYE07rxbh-q2pHjsPrUXVYg"
API_KEY = "5911714ce3ffbc56f7064a9ad0708e0c"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def fetch_image(topic):
    # Генерация картинки через отдельный запрос
    payload = {"model": "flux-2/pro-text-to-image", "input": {"prompt": f"Professional presentation cover about {topic}"}}
    task = requests.post("https://api.kie.ai/api/v1/jobs/createTask", json=payload, headers=HEADERS).json()
    task_id = task['data']['taskId']
    
    for _ in range(15):
        time.sleep(5)
        res = requests.get(f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}", headers=HEADERS).json()
        if res['data'].get('resultJson'):
            url = json.loads(res['data']['resultJson'])['resultUrls'][0]
            return requests.get(url).content
    return None

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Пришли мне тему для презентации.")

@dp.message(F.text)
async def generate(message: Message):
    topic = message.text
    msg = await message.answer("⏳ Работаю...")
    
    # 1. Текст через JSON
    prompt = "Создай структуру презентации на 3 слайда о " + topic + ". Выдай JSON: [{'title': 'Заголовок', 'content': 'Текст'}]"
    resp = requests.post("https://api.kie.ai/gemini-3.1-pro/v1/chat/completions", 
                         json={"messages": [{"role": "user", "content": prompt}]}, headers=HEADERS).json()
    data = json.loads(resp['choices'][0]['message']['content'].replace("```json", "").replace("```", ""))

    # 2. Картинка (выполняем в отдельном потоке, чтобы не вешать бота)
    img_data = await asyncio.to_thread(fetch_image, topic)

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
    import time
    asyncio.run(main())
