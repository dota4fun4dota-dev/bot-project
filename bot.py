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
from docx import Document

# Твой токен
BOT_TOKEN = "8957490808:AAEWFUdFyV8cpYE07rxbh-q2pHjsPrUXVYg"
API_KEY = "5911714ce3ffbc56f7064a9ad0708e0c" 
CHAT_API_URL = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    waiting_for_topic = State()

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Презентация (.pptx)", callback_data="type_pptx")],
        [InlineKeyboardButton(text="📄 Документ (.docx)", callback_data="type_docx")]
    ])

@dp.startup()
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! Выберите формат материала:", reply_markup=get_main_menu())

@dp.callback_query(F.data.startswith("type_"))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    file_type = callback.data.split("_")[1]
    await state.update_data(file_type=file_type)
    await state.set_state(Form.waiting_for_topic)
    await callback.message.edit_text(f"Выбрано: {file_type.upper()}. Напишите тему.")
    await callback.answer()

@dp.message(Form.waiting_for_topic)
async def process_topic(message: Message, state: FSMContext):
    user_data = await state.get_data()
    file_type = user_data.get("file_type")
    topic = message.text
    msg = await message.answer(f"⏳ Генерирую {file_type.upper()} на тему: '{topic}'...")

    # Исправленный промпт с двойными фигурными скобками
    prompt = f"Создай структуру из 5 слайдов/разделов на тему '{topic}'. Выдай ответ СТРОГО в формате JSON списком объектов: [{{'title': 'Заголовок', 'content': 'Текст'}}, ...]"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(CHAT_API_URL, json={"messages": [{"role": "user", "content": prompt}]},
                                   headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
            
            content = resp.json()['choices'][0]['message']['content']
            clean_json = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            if file_type == "pptx":
                prs = Presentation()
                for item in data:
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    slide.shapes.title.text = item.get('title', 'Без названия')
                    slide.placeholders[1].text = item.get('content', '')
                filename = f"presentation_{message.from_user.id}.pptx"
                prs.save(filename)
            else:
                doc = Document()
                for item in data:
                    doc.add_heading(item.get('title', 'Без названия'), level=1)
                    doc.add_paragraph(item.get('content', ''))
                filename = f"document_{message.from_user.id}.docx"
                doc.save(filename)

            await message.answer_document(FSInputFile(filename))
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"Ошибка при генерации: {str(e)}")
    
    await state.clear()

async def main():
    await dp.start_polling(bot)
