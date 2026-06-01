import asyncio
import logging
import httpx
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
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

class Form(StatesGroup):
    waiting_for_topic = State()

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await message.answer("Введите тему для презентации (будет сгенерирована с картинкой на первом слайде):")
    await state.set_state(Form.waiting_for_topic)

@dp.message(Form.waiting_for_topic)
async def process_topic(message: Message, state: FSMContext):
    topic = message.text
    msg = await message.answer("⏳ Создаю презентацию...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # 1. Текст
        prompt = f"Создай структуру из 3 слайдов на тему '{topic}'. JSON: [{'title': '...', 'content': '...'}, ...]"
        resp = await client.post(CHAT_API_URL, json={"messages": [{"role": "user", "content": prompt}]}, 
                               headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
        data = json.loads(resp.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip())

        # 2. Картинка (через KIE API)
        task_resp = await client.post(f"{IMG_API_URL}/createTask", json={"model": "flux-2/pro-text-to-image", "input": {"prompt": f"Professional presentation cover for {topic}"}}, headers={"Authorization": f"Bearer {API_KEY}"})
        task_id = task_resp.json()['data']['taskId']
        
        img_url = None
        for i in range(10):
            await asyncio.sleep(6)
            res = await client.get(f"{IMG_API_URL}/recordInfo?taskId={task_id}", headers={"Authorization": f"Bearer {API_KEY}"})
            status_data = res.json().get("data", {})
            if status_data.get("resultJson"):
                img_url = json.loads(status_data["resultJson"]).get("resultUrls", [None])[0]
                break
        
        # 3. Сборка
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = topic
        if img_url:
            img_req = await client.get(img_url)
            slide.shapes.add_picture(BytesIO(img_req.content), Inches(1), Inches(2), width=Inches(4))
        
        for item in data:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = item.get('title')
            slide.placeholders[1].text = item.get('content')
            
        prs.save("final.pptx")
        await message.answer_document(FSInputFile("final.pptx"))
        await msg.delete()
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
