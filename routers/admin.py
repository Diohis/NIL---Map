import logging
import os
import gspread
from aiogram import Router, types,F,Bot
from aiogram.filters import Command,CommandStart, BaseFilter
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

class Find(StatesGroup):
    forms = State()
class Load(StatesGroup):
    forms = State()

def create_admin_buttons()->InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="Найти",
        callback_data=f"admin_find")
    )
    builder.add(types.InlineKeyboardButton(
        text="Выгрузка",
        callback_data=f"admin_load")
    )
    builder.row(types.InlineKeyboardButton(
        text="Рассылка",
        callback_data="admin_letter")
    )
    builder.row(types.InlineKeyboardButton(
        text="Завершить",
        callback_data="admin_hide")
    )
    return builder 

def create_buttons(type:str,action:int,data:list)->InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="<--",
        callback_data=f"{type}_{action-1}")
    )
    if action+1<len(data):
        builder.add(types.InlineKeyboardButton(
            text="-->",
            callback_data=f"{type}_{action+1}")
        )
    builder.row(types.InlineKeyboardButton(
        text="Прекратить просмотр",
        callback_data=f"{type}_-1")
    )
    return builder

def create_form_message(people:dict)->str:
    message = f"ФИО: {people[0]}\nТелефон: {people[1]}"
    return message
@router.message(Command(commands=["cancel"]))
@router.message(F.text.casefold() == "cancel")
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info("Cancelling state %r", current_state)
    await state.clear()

@router.message(Command("admin"))
async def command_recipe_handler(message: Message,state: FSMContext):
    worksheet = sheet.worksheet("Adress_Admin")
    if worksheet.findall(f"{message.from_user.id}")==[]:
        await message.reply("Отказано в доступе")
        return
    builder = create_admin_buttons()
    await message.answer("Добро пожаловать в админ панель!",reply_markup=builder.as_markup())
    
@router.callback_query(F.data.startswith("find_"))
async def callbacks_form(callback: types.CallbackQuery,state: FSMContext):
    action = int(callback.data.split("_")[1])
    data = await state.get_data()
    data = data["forms"]
    if action == -1:
        await cmd_cancel(message = callback.message,state = state)
        await callback.message.delete()
        await callback.answer()
    else:
        builder = create_buttons("find",action,data)
        await callback.message.edit_text(create_form_message(data[action]),reply_markup=builder.as_markup())
@router.callback_query(F.data.startswith("load_"))
async def callbacks_form(callback: types.CallbackQuery,state: FSMContext,bot:Bot):
    action = int(callback.data.split("_")[1])
    data = await state.get_data()
    data = data["forms"]
    if action == -1:
        await cmd_cancel(message = callback.message,state = state)
        await callback.message.delete()
        await callback.answer()
    else:
        builder = create_buttons("load",action,data)
        await callback.message.edit_live_location(latitude=float(data[action][0]),longitude=float(data[action][1]),reply_markup=builder.as_markup())                 
@router.callback_query(F.data.startswith("admin_"))
async def callbacks_admin_panel(callback: types.CallbackQuery,state: FSMContext,bot:Bot):
    action = callback.data.split("_")[1]
    if action == "find":
        worksheet = sheet.worksheet("Adress_Info")
        
        await state.set_state(Find.forms)
        
        await state.update_data(forms = worksheet.get_all_values()[1:]) #занести в state массив анкет из таблицы
        data = await state.get_data()
        data = data["forms"]
        builder = create_buttons(action,0,data)
        await callback.message.answer(create_form_message(data[0]),reply_markup=builder.as_markup())
        await callback.answer()
    if action == "load":
        worksheet = sheet.worksheet("Adress_Info")
        await state.set_state(Load.forms)
        xy = worksheet.col_values(3)[1:]
        xy = [i.split(",") for i in xy]
        await state.update_data(forms = xy) #занести в state массив координат из таблицы
        data = await state.get_data()
        data = data["forms"]
        builder = create_buttons(action,0,data)
        msg = await bot.send_location(chat_id=callback.message.chat.id,latitude=data[0][0],longitude=data[0][1],live_period=3600,reply_markup=builder.as_markup())
        await callback.answer()
    if action == "hide":
        await callback.answer()
        await callback.message.delete()