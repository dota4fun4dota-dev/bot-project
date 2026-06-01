import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Токен вставлен
BOT_TOKEN = "8957490808:AAEWFUdFyV8cpYE07rxbh-q2pHjsPrUXVYg"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния бота
class Form(StatesGroup):
    waiting_for_topic = State()

# Меню выбора
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Презентация (.pptx)", callback_data="type_pptx")],
        [InlineKeyboardButton(text="📄 Документ (.docx)", callback_data="type_docx")]
    ])

@dp.startup()
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен.")

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Выберите формат материала:", reply_markup=get_main_menu())

@dp.callback_query(F.data.startswith("type_"))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    file_type = callback.data.split("_")[1]
    # Сохраняем выбор в состояние FSM
    await state.update_data(file_type=file_type)
    await state.set_state(Form.waiting_for_topic)
    
    await callback.message.edit_text(
        f"Выбрано: {file_type.upper()}. Теперь напишите тему, по которой нужно подготовить материал."
    )
    await callback.answer()

@dp.message(Form.waiting_for_topic)
async def process_topic(message: Message, state: FSMContext):
    user_data = await state.get_data()
    file_type = user_data.get("file_type")
    topic = message.text
    
    await message.answer(f"Принято! Создаю {file_type.upper()} на тему: '{topic}'. Пожалуйста, подождите...")
    
    # ЗДЕСЬ МЫ ПОЗЖЕ ПОДКЛЮЧИМ ИИ
    # await generate_material(topic, file_type, message)
    
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
