import logging
import os
import gspread
from aiogram import Router, types,F,Bot
from aiogram.filters import CommandStart, BaseFilter
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder,InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()
scope = ['https://www.googleapis.com/auth/spreadsheets']
credentials = Credentials.from_service_account_file('cred.json')
client = gspread.authorize(credentials.with_scopes(scope))
sheet = client.open_by_url(os.getenv("SHEET_URL"))

router = Router()

class Form(StatesGroup):
    nso = State()
    phone = State()
    location = State()

class NSOFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return len(message.text.split())==3


@router.message(CommandStart())
async def command_start(message: Message) -> None:
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Начать",callback_data = "start"))
    await message.answer(
        f"Приветствую {message.from_user.username} в боте сборщика информации",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )
    worksheet = sheet.worksheet("Adress_Contact")
    if worksheet.findall(f"{message.from_user.id}")==[]:
        column_index = 1
        row_index = len(worksheet.get_all_values())+1
        worksheet.update_cell(row_index, column_index, message.from_user.id)
        worksheet.update_cell(row_index, column_index+1, message.from_user.first_name)   

@router.callback_query(F.data == "start")
async def callbacks_num(callback: types.CallbackQuery,state: FSMContext):
    await state.set_state(Form.nso)
    await callback.message.answer("Напишите свое ФИО через пробел")
    await callback.answer()


@router.message(Form.nso,NSOFilter())
async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(nso=message.text)
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Поделиться контактом.", request_contact=True))
    await message.answer(
        f"Отлично! Теперь отправьте свой номер телефона.",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )
    await state.set_state(Form.phone)

@router.message(Form.nso)
async def nso_incorrectly(message: Message):
    await message.answer(
        text="Вы написали некорректное ФИО, повторите попытку.",
    )

@router.message(Form.phone,(F.contact!=None and F.contact.user_id == F.from_user.id))
async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.contact.phone_number)
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Поделиться местоположенем.", request_location=True))
    await message.answer(
        f"Отлично! Теперь укажите свое местоположение.",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )
    await state.set_state(Form.location)


@router.message(Form.location)
async def process_name(message: Message, state: FSMContext, bot = Bot) -> None:
    await state.update_data(location=message.location)
    data = await state.get_data()
    await state.clear()
    nso = data["nso"]
    phone = data["phone"]
    adress = f"{data["location"].latitude},{data["location"].longitude}"
    worksheet = sheet.worksheet("Adress_Info")
    if worksheet.findall(str(phone)[1:])!=[]:
        await message.reply("Вы уже поделились информацией ранее!")
        return
    column_index = 1
    row_index = len(worksheet.get_all_values())+1
    worksheet.update_cell(row_index, column_index, nso)
    worksheet.update_cell(row_index, column_index+1, phone)
    worksheet.update_cell(row_index, column_index+2, adress)
    await message.reply("Спасибо за информацию!")   
    
