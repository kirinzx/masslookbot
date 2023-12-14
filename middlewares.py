from aiogram import Dispatcher
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineQuery
import aiosqlite

class AdminMiddleware(BaseMiddleware):
    async def on_process_message(self, message: Message, data: dict):
        await self.checkForAdmin(str(message.from_user.id))

    async def on_process_callback_query(self, call: CallbackQuery, data: dict):
        await self.checkForAdmin(str(call.from_user.id))

    async def on_process_inline_query(self, query: InlineQuery, data: dict):
        await self.checkForAdmin(str(query.from_user.id))


    async def checkForAdmin(self, userId: int):
        async with aiosqlite.connect("masslook.db") as db:
            async with db.execute("SELECT adminId FROM admins") as cur:
                admins = [admin[0] for admin in await cur.fetchall()]
        if not userId in admins:
            raise CancelHandler