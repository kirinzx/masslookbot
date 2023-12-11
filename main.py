from classes.storywatcher import StoryWatcher
from handlers import main as bot_main
import sqlite3, asyncio

def create_tables():
    con = sqlite3.connect('masslook.db')
    cur = con.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY, nickname TEXT NOT NULL UNIQUE, adminId TEXT NOT NULL UNIQUE);"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, phoneNumber TEXT NOT NULL UNIQUE, app_id TEXT NOT NULL UNIQUE, app_hash TEXT NOT NULL UNIQUE, proxy TEXT, stories_watched INTEGER NOT NULL DEFAULT 0);"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS chat_users(id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, FOREIGN KEY (user_id) REFERENCES user(id))"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS parsed_users(user_id INTEGER PRIMARY KEY, stories_max_id TEXT NOT NULL, chat_id INTEGER NOT NULL);"
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


def main():
    create_tables()
    loop = asyncio.get_event_loop()
    set_watchers(loop)
    bot_main(loop)

if __name__ == '__main__':
    main()