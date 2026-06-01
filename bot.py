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

# Токен
BOT_TOKEN = "8957490808:AAEWFUdFyV8cpYE07rxbh-q2pHjsPrUXVYg"
API_KEY = "5911714ce3ffbc56f7064a9ad0708e0c" 
CHAT_API_URL = "https://api.kie.ai/gemini-3.1-pro/v1/chat/completions"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    choosing_type = State()
    choosing_count = State()
    waiting_for_topic = State()

def get_type_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Презентация (.pptx)", callback_data="type_pptx")],
        [InlineKeyboardButton(text="📄 Документ (.docx)", callback_data="type_docx")]
    ])

def get_count_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 страниц", callback_data="count_5"), 
         InlineKeyboardButton(text="10 страниц", callback_data="count_10")]
    ])

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await message.answer("Выберите формат:", reply_markup=get_type_menu())
    await state.set_state(Form.choosing_type)

@dp.callback_query(Form.choosing_type)
async def choose_type(callback: CallbackQuery, state: FSMContext):
    await state.update_data(file_type=callback.data.split("_")[1])
    await callback.message.edit_text("Выберите объем:", reply_markup=get_count_menu())
    await state.set_state(Form.choosing_count)

@dp.callback_query(Form.choosing_count)
async def choose_count(callback: CallbackQuery, state: FSMContext):
    await state.update_data(count=callback.data.split("_")[1])
    await callback.message.edit_text("Теперь напишите тему материала:")
    await state.set_state(Form.waiting_for_topic)

@dp.message(Form.waiting_for_topic)
async def process_topic(message: Message, state: FSMContext):
    user_data = await state.get_data()
    file_type = user_data.get("file_type")
    count = user_data.get("count")
    topic = message.text
    
    msg = await message.answer("⏳ Генерирую...")
    prompt = f"Создай детальную структуру на {count} разделов на тему '{topic}'. Выдай JSON: [{{'title': 'Заголовок', 'content': 'Текст'}}, ...]"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(CHAT_API_URL, json={"messages": [{"role": "user", "content": prompt}]}, 
                                   headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
            data = json.loads(resp.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip())

            if file_type == "pptx":
                prs = Presentation()
                for item in data:
                    slide = prs.slides.add_slide(prs.slide_layouts[1])
                    slide.shapes.title.text = item.get('title', '...')
                    slide.placeholders[1].text = item.get('content', '')
                filename = "result.pptx"
                prs.save(filename)
            else:
                doc = Document()
                for item in data:
                    doc.add_heading(item.get('title', '...'), level=1)
                    doc.add_paragraph(item.get('content', ''))
                filename = "result.docx"
                doc.save(filename)

            await message.answer_document(FSInputFile(filename))
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"Ошибка: {str(e)}")
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
