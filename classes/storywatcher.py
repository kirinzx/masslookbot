from telethon import TelegramClient, functions
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio, logging, aiosqlite, python_socks

class StoryWatcher:
    def __init__(self, id, phone_number, api_id, api_hash, proxy, loop, strories_watched=0):
        self.__phone_number = phone_number
        self.proxy = proxy
        self.__id = id
        self.__api_id = int(api_id)
        self.__api_hash = api_hash
        self.__stories_watched = strories_watched
        self.loop: asyncio.AbstractEventLoop = loop
        self.__initialize()

    def __initialize(self):
        self.scheduler = AsyncIOScheduler(event_loop=self.loop)
        self.__set_client()
        self.client.start()
        self.loop.create_task(self.__get_chats_from_db())
        story_watchers.append(self)
        self.__set_schedule()

    def __set_client(self):
        self.client = TelegramClient(session=f"sessions/{self.__phone_number}", api_id=self.__api_id, api_hash=self.__api_hash, loop=self.loop, app_version="4.0",system_version="IOS 14",device_model="iPhone 14")
        if self.proxy is not None:
            split_proxy = self.proxy.split(':')
            self.proxy = (python_socks.ProxyType.SOCKS5,split_proxy[0],split_proxy[1],True,split_proxy[2],split_proxy[3])
            self.client.set_proxy(self.proxy)


    async def __get_chats_from_db(self):
        async with aiosqlite.connect('masslook.db') as db:
            async with db.execute(f"SELECT chat_id FROM chat_users WHERE user_id={self.__id}") as cur:
                async for chat_id in cur:
                    await self.__parse_users_from_chat(chat_id)

    async def __save_parsed_user(self, user_id, stories_max_id, chat_id):
        async with aiosqlite.connect("masslook.db") as db:
            await db.execute(f"INSERT INTO parsed_users(user_id, stories_max_id, chat_id) VALUES ({user_id},{stories_max_id},{chat_id});")
            await db.commit()

    async def __parse_users_from_chat(self, chat):
        async for user in self.client.iter_participants(chat, limit=10):
            if (
                not user.stories_unavailable and 
                not user.stories_hidden and 
                user.stories_max_id
            ):
                await self.__save_parsed_user(user.id, user.stories_max_id, chat)

    async def __get_users_from_db(self):
        async with aiosqlite.connect('masslook.db') as db:
            async with db.execute(f"SELECT chat_id FROM chat_users WHERE user_id={self.__id};") as cursor:
                async for chat_id in cursor:
                    async with db.execute(f'SELECT user_id, stories_max_id FROM parsed_users WHERE chat_id={chat_id[0]};') as cur:
                        async for user in cur:
                            try:
                                await self.__watch_story(user[0], user[1])
                                asyncio.sleep(15)
                            except Exception as e:
                                logging.info(f"Error in get users from db! {e}")

    async def __watch_story(self, indentity, stories_max_id):
        
        result = await self.client(functions.stories.ReadStoriesRequest(
            peer=indentity,
            max_id=stories_max_id
        ))

        self.__stories_watched += len(result)

    async def __change_stories_watched(self):
        async with aiosqlite.connect('masslook.db') as db:
            await db.execute(f'UPDATE users SET stories_watched={self.__stories_watched} WHERE id={self.__id};')
            await db.commit()

    async def __entry(self):
        await self.__get_users_from_db()
        await self.__change_stories_watched()

    def stop(self):
        story_watchers.remove(self)

    def __set_schedule(self):
        self.loop.create_task(self.__entry)
        self.scheduler.add_job(self.__entry,IntervalTrigger(days=1))
        self.scheduler.start()

story_watchers = []