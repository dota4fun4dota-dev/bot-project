import asyncio
import logging
import httpx
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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

# --- Вспомогательная функция для генерации картинки ---
async def generate_and_get_image(client, prompt):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    # Создаем задачу
    task = await client.post(f"{IMG_API_URL}/createTask", json={"model": "flux-2/pro-text-to-image", "input": {"prompt": prompt}}, headers=headers)
    task_id = task.json().get("data", {}).get("taskId")
    
    # Ждем результат
    for _ in range(10):
        await asyncio.sleep(5)
        res = await client.get(f"{IMG_API_URL}/recordInfo?taskId={task_id}", headers=headers)
        data = res.json().get("data", {})
        if data.get("resultJson"):
            url = json.loads(data["resultJson"]).get("resultUrls", [None])[0]
            if url:
                img_resp = await client.get(url)
                return BytesIO(img_resp.content)
    return None

# --- Обработка создания (основной блок) ---
@dp.message(F.text) # Здесь логика, где вызывается процесс
async def process_topic(message: Message, state: FSMContext):
    # ... (код получения данных из state) ...
    
    # В цикле по слайдам:
    for item in data:
        slide = prs.slides.add_slide(prs.slide_layouts[5]) # Макет "Только заголовок"
        slide.shapes.title.text = item.get('title')
        
        # Генерируем картинку
        img_io = await generate_and_get_image(client, item.get('image_prompt', 'abstract design'))
        if img_io:
            slide.shapes.add_picture(img_io, Inches(1), Inches(1.5), height=Inches(4))
        
        # Добавляем текст
        txBox = slide.shapes.add_textbox(Inches(6), Inches(1.5), Inches(4), Inches(4))
        txBox.text = item.get('content')
