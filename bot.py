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
IMG_API_URL = "https://api.kie.ai/api/v1/jobs"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    choosing_type = State()
    choosing_count = State()
    waiting_for_topic = State()

# --- Вспомогательная функция для картинок ---
async def get_image_url(client, prompt):
    try:
        task = await client.post(f"{IMG_API_URL}/createTask", 
                               json={"model": "flux-2/pro-text-to-image", "input": {"prompt": prompt}}, 
                               headers={"Authorization": f"Bearer {API_KEY}"})
        task_id = task.json().get("data", {}).get("taskId")
        for _ in range(15):
            await asyncio.sleep(5)
            res = await client.get(f"{IMG_API_URL}/recordInfo?taskId={task_id}", headers={"Authorization": f"Bearer {API_KEY}"})
            data = res.json().get("data", {})
            if data.get("resultJson"):
                return json.loads(data["resultJson"]).get("resultUrls", [None])[0]
    except: return None
    return None

# --- Меню и обработчики (остались прежними) ---
def get_type_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📊 Презентация (.pptx)", callback_data="type_pptx")]])

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await message.answer("Выберите формат:", reply_markup=get_type_menu())
    await state.set_state(Form.choosing_type)

@dp.callback_query(Form.choosing_type)
async def choose_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(file_type=callback.data.split("_")[1])
    await callback.message.edit_text("Введите тему:")
    await state.set_state(Form.waiting_for_topic)

@dp.message(Form.waiting_for_topic)
async def process_topic(message: Message, state: FSMContext):
    topic = message.text
    msg = await message.answer("⏳ Генерирую презентацию с картинками (это займет время)...")
    
    prompt = f"Создай структуру из 5 слайдов на тему '{topic}'. Добавь поле 'image_desc' для каждого слайда. JSON: [{{'title': '...', 'content': '...', 'image_desc': '...'}}, ...]"
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(CHAT_API_URL, json={"messages": [{"role": "user", "content": prompt}]}, 
                               headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
        data = json.loads(resp.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip())

        prs = Presentation()
        for item in data:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = item.get('title')
            slide.placeholders[1].text = item.get('content')
            
            # Вставка картинки
            img_url = await get_image_url(client, item.get('image_desc'))
            if img_url:
                img_data = await client.get(img_url)
                slide.shapes.add_picture(BytesIO(img_data.content), Inches(6), Inches(2), width=Inches(3))

        filename = "presentation.pptx"
        prs.save(filename)
        await message.answer_document(FSInputFile(filename))
        await msg.delete()
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
