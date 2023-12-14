from shutil import ExecError
from telethon import TelegramClient, functions, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio, logging, aiosqlite, python_socks, async_timeout, socks

class StoryWatcher:
    def __init__(self, id, phone_number, api_id, api_hash, proxy, loop, strories_watched=0):
        self.phone_number = phone_number
        self.proxy = proxy
        self.__id = id
        self.__api_id = int(api_id)
        self.__api_hash = api_hash
        self.stories_watched = strories_watched
        self.running = True
        self.loop: asyncio.AbstractEventLoop = loop
        self.__initialize()

    def __initialize(self):
        try:
            self.scheduler = AsyncIOScheduler(event_loop=self.loop)
            self.__set_client()
            story_watchers[self.phone_number] = self
            self.loop.create_task(self.get_chats_from_db())
            self.__set_schedule()
        except Exception as e:
            logging.error(f'error in init. {self.phone_number}. {e}')

    def __set_client(self):
        self.client = TelegramClient(session=f"sessions/{self.phone_number}", api_id=self.__api_id, api_hash=self.__api_hash, loop=self.loop, app_version="4.0",system_version="IOS 14",device_model="iPhone 14")
        if self.proxy is not None:
            split_proxy = self.proxy.split(':')
            self.proxy = (python_socks.ProxyType.SOCKS5,split_proxy[0],split_proxy[1],True,split_proxy[2],split_proxy[3])
            self.client.set_proxy(self.proxy)

    async def save_chat(self, chat_link, nickname):
        try:
            async with self.client as client:
                chat = await client.get_input_entity(chat_link)
                if isinstance(chat, types.InputPeerChannel):
                    chat_tg_id = chat.channel_id
                elif isinstance(chat, types.InputPeerChat):
                    chat_tg_id = chat.chat_id
            async with aiosqlite.connect('masslook.db') as db:
                cursor = await db.cursor()
                try:
                    await cursor.execute("INSERT INTO chats(chat_id, nickname) VALUES (?, ?);", (chat_tg_id, nickname))
                    chat_id = cursor.lastrowid
                    parsed = False
                except aiosqlite.IntegrityError:
                    await cursor.execute("SELECT id, parsed FROM chats WHERE chat_id = ?;", (chat_tg_id,))
                    tmp = await cursor.fetchone()
                    chat_id = tmp[0]
                    parsed = int(tmp[1])
                
                await cursor.execute("INSERT INTO chat_users(chat_id, user_id) VALUES (?,?);", (chat_id, self.__id))
                await db.commit()
            if not parsed:
                await self.__parse_users_from_chat(chat_id, chat_tg_id, chat)
                async with aiosqlite.connect('masslook.db') as db:
                    await db.execute("UPDATE chats SET parsed = 1 WHERE id = ?;",(chat_id,))
                    await db.commit()
            await self.__get_users_from_db()
        except Exception as e:
            logging.error(f'error in save. {self.phone_number}. {e}')


    async def get_chats_from_db(self):
        try:
            async with aiosqlite.connect('masslook.db') as db:
                async with db.execute("SELECT chats.id, chats.chat_id FROM chats JOIN chat_users ON user_id=? WHERE parsed=0;",(self.__id,)) as cur:
                    async for chat in cur:
                        await self.__parse_users_from_chat(chat[0], chat[1])
                        await db.execute("UPDATE chats SET parsed = 1 WHERE id=?;",(chat[0],))
                        await db.commit()
        except Exception as e:
            logging.error(f'error in get chats from db. {self.phone_number}. {e}')

    async def __save_parsed_users(self, users):
        try:
            async with aiosqlite.connect("masslook.db") as db:
                await db.executemany(f"INSERT INTO parsed_users(user_id, stories_max_id, chat_id) VALUES (?,?,?);", users)
                await db.commit()
        except Exception as e:
            logging.error(f'error in save parsed users. {e}')

    async def __parse_users_from_chat(self, chat_db_id, chat_id, instance=None):
        users = []
        try:
            async with self.client as client:
                    if instance is None:
                        chat_instance = await client.get_input_entity(int(chat_id))
                    else:
                        chat_instance = instance
                    async for user in client.iter_participants(chat_instance, limit=1000000):
                        if (
                            not user.stories_unavailable and 
                            not user.stories_hidden and 
                            user.stories_max_id
                        ):
                            users.append((user.id, user.stories_max_id, chat_db_id))
                            await asyncio.sleep(2)
                        await asyncio.sleep(1)
                    await self.__save_parsed_users(users)
        except Exception as e:
            logging.error(f'error in parse users from chat. {self.phone_number}. chat_id = {chat_db_id}. {e}')

    async def __get_users_from_db(self):
        try:
            async with aiosqlite.connect('masslook.db') as db:
                async with db.execute(f"SELECT parsed_users.user_id, parsed_users.stories_max_id FROM parsed_users\
                                        JOIN chats ON parsed_users.chat_id = chats.id JOIN chat_users ON chat_users.id\
                                        = chat_users.chat_id WHERE chat_users.user_id = ? AND chats.parsed = 1;", (self.__id,)
                ) as cursor:
                    async for user in cursor:
                        await self.__watch_story(user[0], 2147483647)
                        logging.error(f'{self.phone_number} watched story of {user}')
                        await asyncio.sleep(3)
        except Exception as e:
            logging.error(f'error in get users from db. {self.phone_number}. {e}')
                    

    async def __watch_story(self, indentity, stories_max_id):
        try:
            async with self.client as client:
                result = await client(functions.stories.ReadStoriesRequest(
                    peer=indentity,
                    max_id=stories_max_id
                ))

                self.stories_watched += len(result)
        except Exception as e:
            logging.error(f'error in watch story. {self.phone_number}. {e}')

    async def __change_stories_watched(self):
        try:
            async with aiosqlite.connect('masslook.db') as db:
                await db.execute(f'UPDATE users SET stories_watched={self.stories_watched} WHERE id={self.__id};')
                await db.commit()
        except Exception as e:
            logging.error(f'error in change stories watched. {self.phone_number}. {e}')

    async def __entry(self):
        if self.running:
            await self.__get_users_from_db()
            await self.__change_stories_watched()

    async def stop(self):
        await self.client.disconnect()
        async with aiosqlite.connect("masslook.db") as db:
            await db.execute("DELETE FROM chat_users WHERE user_id=?;",(self.__id,))
            await db.execute("DELETE FROM users WHERE id=?;",(self.__id,))
            await db.commit()
        del story_watchers[self.phone_number]

    def __set_schedule(self):
        self.loop.create_task(self.__entry())
        self.scheduler.add_job(self.__entry,IntervalTrigger(days=1))
        self.scheduler.start()

story_watchers: dict[str, StoryWatcher] = {}