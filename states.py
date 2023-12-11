from aiogram.dispatcher.filters.state import State, StatesGroup

class AdminForm(StatesGroup):
    nickname = State()
    adminId = State()

class UserForm(StatesGroup):
    phoneNumber = State()
    app_id = State()
    app_hash = State()
    proxy = State()
    code = State()
    password = State()