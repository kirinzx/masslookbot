from classes.storywatcher import StoryWatcher
from handlers import main as bot_main
import sqlite3, asyncio, logging

def create_tables():
    con = sqlite3.connect('masslook.db')
    cur = con.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY, nickname TEXT NOT NULL UNIQUE,\
        adminId TEXT NOT NULL UNIQUE);"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, phoneNumber TEXT NOT NULL UNIQUE,\
        app_id TEXT NOT NULL UNIQUE, app_hash TEXT NOT NULL UNIQUE, proxy TEXT, stories_watched INTEGER NOT NULL DEFAULT 0);"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY, nickname TEXT NOT NULL, chat_id INTEGER NOT NULL UNIQUE, parsed INTEGER NOT NULL default 0)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS chat_users(id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL,\
        user_id INTEGER NOT NULL, FOREIGN KEY (chat_id) REFERENCES chats(id), FOREIGN KEY (user_id) REFERENCES users(id))"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS parsed_users(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,\
        stories_max_id INTEGER NOT NULL, chat_id INTEGER NOT NULL, FOREIGN KEY(chat_id) REFERENCES chats(id));"
    )
    con.commit()
    con.close()

def set_watchers(loop):
    con = sqlite3.connect('masslook.db')
    cur = con.cursor()
    cur.execute("SELECT * FROM users")
    for user in cur.fetchall():
        StoryWatcher(user[0],user[1],user[2],user[3],user[4],loop,user[5])
    con.close()

def create_admins():
    con = sqlite3.connect('masslook.db')
    cur = con.cursor()
    with open('admins.txt') as file:
        admins = file.readlines()
        for i in range(len(admins)):
            admins[i] = admins[i].split(' ')
        cur.executemany("INSERT OR IGNORE INTO admins(nickname, adminId) VALUES (?,?);",admins)
        con.commit()
        con.close()

def main():
    logging.basicConfig(level=logging.ERROR)
    create_tables()
    create_admins()
    loop = asyncio.get_event_loop()
    set_watchers(loop)
    bot_main(loop)

if __name__ == '__main__':
    main()