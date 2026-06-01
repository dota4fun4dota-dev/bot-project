import asyncio
import logging
import httpx
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from pptx import Presentation
from pptx.util import Inches
from io import BytesIO

BOT_TOKEN = "8957490808:AAEWFUdFyV8cpYE07rxbh-q2pHjsPrUXVYg"
API_KEY = "5911714ce3ffbc56f7064a9ad0708e0c" 
CHAT_API_URL = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"
IMG_API_URL = "https://api.kie.ai/api/v1/jobs/createTask"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    choosing_count = State()
    waiting_for_topic = State()

# Меню выбора страниц
def get_count_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 слайдов", callback_data="count_5"), InlineKeyboardButton(text="10 слайдов", callback_data="count_10")]
    ])

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await message.answer("Выберите количество слайдов:", reply_markup=get_count_menu())
    await state.set_state(Form.choosing_count)

@dp.callback_query(Form.choosing_count)
async def choose_count(callback: CallbackQuery, state: FSMContext):
    count = callback.data.split("_")[1]
    await state.update_data(count=count)
    await state.set_state(Form.waiting_for_topic)
    await callback.message.edit_text(f"Выбрано: {count} слайдов. Теперь напишите тему презентации.")
    await callback.answer()

@dp.message(Form.waiting_for_topic)
async def process_topic(message: Message, state: FSMContext):
    user_data = await state.get_data()
    count = user_data.get("count")
    topic = message.text
    msg = await message.answer("⏳ Генерирую контент и подбираю изображения...")

    # Промпт для ИИ
    prompt = f"Создай детальный контент для презентации на {count} слайдов на тему '{topic}'. Ответ строго JSON: [{'title': '...', 'content': '...', 'image_prompt': '...'}]"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Получаем текст
        resp = await client.post(CHAT_API_URL, json={"messages": [{"role": "user", "content": prompt}]}, headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
        data = json.loads(resp.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip())

        prs = Presentation()
        for item in data:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = item['title']
            slide.placeholders[1].text = item['content']
            
            # Генерация картинки для слайда
            img_resp = await client.post(IMG_API_URL, json={"model": "flux-2/pro-text-to-image", "input": {"prompt": item['image_prompt']}}, headers={"Authorization": f"Bearer {API_KEY}"})
            task_id = img_resp.json()['data']['taskId']
            # (Здесь логика ожидания получения ссылки на фото через recordInfo, как мы делали раньше)
            # Вставляем фото: slide.shapes.add_picture(BytesIO(image_data), left, top, height=Inches(3))
        
        filename = "presentation.pptx"
        prs.save(filename)
        await message.answer_document(FSInputFile(filename))
        await msg.delete()
    await state.clear()
