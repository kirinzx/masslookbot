from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types.inline_keyboard import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import Text
import telethon
from telethon import TelegramClient
import asyncio, aiosqlite, python_socks, async_timeout, socks, os
from tools import getSetting
from middlewares import AdminMiddleware
from states import *
from classes.paginator import Paginator
from classes.user import User
from classes.storywatcher import StoryWatcher


bot = Bot(token=getSetting('bot_token'))
storage = MemoryStorage()
dp = Dispatcher(bot)

client = None
user = None
loop = None

keyboardMain = ReplyKeyboardMarkup(keyboard=[
    [r'Добавить "админа"',"Добавить аккаунт для масслукинга"],
    ["Как я работаю?",'Изменить настройки'],
    [r'Посмотреть "админов"',"Посмотреть добавленные аккаунты"],
],resize_keyboard=True)

keyboardCancel = ReplyKeyboardMarkup(keyboard=[
    ["Отменить"],
])

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(text='Выберите опцию', reply_markup=keyboardMain)

@dp.message_handler(Text(equals='Отменить'), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Отменено', reply_markup=keyboardMain)

@dp.message_handler(Text(equals='Добавить "админа"'))
async def addAdmin(message:types.Message):
    await AdminForm.nickname.set()
    await message.answer("Напишите никнейм для этого аккаунта",reply_markup=keyboardCancel)

@dp.message_handler(state=AdminForm.nickname)
async def process_phoneNumberAdmin(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['nickname'] = message.text.strip()
    await AdminForm.next()
    await message.reply("Напишите id аккаунта",reply_markup=keyboardCancel)

@dp.message_handler(state=AdminForm.adminId)
async def process_adminId(message:types.Message,state:FSMContext):
    async with state.proxy() as data:
        data['adminId'] = message.text.strip()

    async with aiosqlite.connect("accounts.db")as db:
        try:
            if data["adminId"].isdigit():
                await db.execute("INSERT INTO admins(nickname,adminId) VALUES(?,?);",(data["nickname"],data["adminId"]))
                await db.commit()
                await message.reply("Готово!", reply_markup=keyboardMain)
            else:
                await message.reply("Некорректные данные!", reply_markup=keyboardMain)
        except aiosqlite.IntegrityError:
            await message.reply("Админ с такими данными уже сущетсвует!",reply_markup=keyboardMain)
        finally:
            await state.finish()

@dp.message_handler(Text(equals=r'Посмотреть "админов"'))
async def getAdmins(message:types.Message):
    async with aiosqlite.connect("accounts.db")as db:
        async with db.execute("SELECT phoneNumber,adminId FROM admins;")as cur:
            admins = await cur.fetchall()
    if len(admins) > 0:
        adminsButtons = InlineKeyboardMarkup()
        for admin in admins:
            if admin[1] == str(message.from_user.id):
                adminsButtons.add(InlineKeyboardButton(text=str(admin[0]), callback_data=f"view {admin[0]}"),
                                  InlineKeyboardButton(text=str(admin[1]), callback_data=f"view {admin[1]}"),
                                  InlineKeyboardButton(text="-", callback_data=f"fake-delete {admin[0]}"))
            else:
                adminsButtons.add(InlineKeyboardButton(text=str(admin[0]), callback_data=f"view {admin[0]}"),
                                  InlineKeyboardButton(text=str(admin[1]),callback_data=f"view {admin[1]}"),
                                  InlineKeyboardButton(text="Удалить", callback_data=f"Удалить админа {admin[0]}"))
        paginator = Paginator(adminsButtons, size=5, dp=dp)
        await message.answer(text="Добавленные админы. Чтобы удалить, нажмите на кнопку удаления",reply_markup=paginator())
    else:
        await message.answer(text="Админов нет...", reply_markup=keyboardMain)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('Удалить админа'))
async def process_callback_deleteAdmin(callback_query: types.CallbackQuery):
    adminToDelete = callback_query.data.split(" ")[-1]
    try:
        async with aiosqlite.connect("accounts.db") as db:
            await db.execute("DELETE FROM admins WHERE phoneNumber=?;", (adminToDelete,))
            await db.commit()

        await bot.send_message(callback_query.from_user.id, text=f"Готово! Админ {adminToDelete} удалён!",
                               reply_markup=keyboardMain)
    except:
        await bot.send_message(callback_query.from_user.id, text="Непридвиденная ошибка!", reply_markup=keyboardMain)

@dp.message_handler(Text(equals="Добавить аккаунт для масслукинга"))
async def addAccount(message:types.Message):
    await UserForm.phoneNumber.set()
    await message.answer(text="Напишите номер телефона(с кодом страны)",reply_markup=keyboardCancel)


@dp.message_handler(state=UserForm.phoneNumber)
async def process_nickname(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phoneNumber'] = message.text.strip()

    await UserForm.next()
    await message.reply("Напишите api_id",reply_markup=keyboardCancel)


@dp.message_handler(state=UserForm.app_id)
async def process_app_id(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['app_id'] = message.text.strip()

    await UserForm.next()
    await message.reply("Напишите api_hash",reply_markup=keyboardCancel)

@dp.message_handler(state=UserForm.app_hash)
async def process_app_hash(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['app_hash'] = message.text.strip()
    await UserForm.next()
    await message.reply("Напишите прокси SOCKS5 в формате ip:port:login:password (если не хотите его использовать, то напишите прочерк(-))",reply_markup=keyboardCancel)

@dp.message_handler(state=UserForm.proxy)
async def process_password(message: types.Message, state: FSMContext):
    try:
        global client, user, loop
        async with state.proxy() as data:
            if proxy != "-":
                split_proxy = proxy.split(':')
                proxy = (python_socks.ProxyType.SOCKS5,split_proxy[0],split_proxy[1],True,split_proxy[2],split_proxy[3])
            else:
                proxy = None
            user = User(data["phoneNumber"], data["app_id"], data["app_hash"], proxy, loop)

        client = TelegramClient(session=f'sessions/{user.phoneNumber}', api_id=int(user.api_id),
                                    api_hash=user.api_hash,app_version="4.0",system_version="IOS 14",device_model="iPhone 14",loop=loop)
        if user.proxy is not None:
            client.set_proxy(proxy)
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone=data["phoneNumber"])
            await message.answer("Введите код, который пришел вам в телеграм. ВНИМАНИЕ! Поставьте в любом месте нижнее подчеркивание(_), иначе придется проходить все этапы регистрации опять!", reply_markup=keyboardCancel)
            await UserForm.next()
        else:
            await saveUser(message,state)
    except Exception as e:
        print(f'Error!{e}')
        await removeSessionFile(user.phoneNumber)
        await message.answer("Непридвиденная ошибка!", reply_markup=keyboardMain)
        await state.finish()

@dp.message_handler(state=UserForm.code)
async def process_code(message: types.Message, state: FSMContext):
    global user
    try:
        await client.sign_in(user.phoneNumber,message.text.strip().replace("_",""))
        await saveUser(message, state)
    except telethon.errors.SessionPasswordNeededError:
        async with state.proxy() as data:
            data["code"] = message.text.strip()
        await UserForm.next()
        await message.answer(text="Введите пароль от 2FA",reply_markup=keyboardCancel)
    except:
        await removeSessionFile(user.phoneNumber)
        await message.answer("Непридвиденная ошибка!", reply_markup=keyboardMain)
        await state.finish()

@dp.message_handler(state=UserForm.password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    try:
        async with state.proxy() as data:
            await client.sign_in(password=password)
            await saveUser(message,state)
    except:
        await removeSessionFile(user.phoneNumber)
        await state.finish()
        await message.answer("Непридвиденная ошибка!",reply_markup=keyboardMain)

async def saveUser(message: types.Message,state: FSMContext):
    try:
        async with aiosqlite.connect("accounts.db") as db:
            await db.execute("INSERT INTO users (phoneNumber, app_id, app_hash, proxy) VALUES(?,?,?,?);",
                             (user.phoneNumber, user.api_id, user.api_hash, user.proxy))
            await db.commit()
        await client.disconnect()
        StoryWatcher(user.phoneNumber, user.api_id, user.api_hash,user.proxy)
        await message.answer("Готово!", reply_markup=keyboardMain)
        await state.finish()
    except aiosqlite.IntegrityError:
        await removeSessionFile(user.phoneNumber)
        await message.answer("Ошибка!Аккаунт с такими данными уже существует!", reply_markup=keyboardMain)
        await state.finish()

async def removeSessionFile(sessionName):
    try:
        os.remove(f"sessions/{sessionName}.session")
    except:
        pass

def main(loop_):
    global loop
    loop = loop_
    asyncio.set_event_loop(loop)
    dp.middleware.setup(AdminMiddleware)
    executor.start_polling(dp, skip_updates=True,loop=loop)
    