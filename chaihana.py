import asyncio
import sqlite3
import random
import time
from datetime import timedelta
from aiogram import Bot, Dispatcher, types, F, html
from aiogram.filters import Command

# --- НАСТРОЙКИ ---
TOKEN = "8542233717:AAFCfC_X3pQjR8JlzLaNGzHwz2Du85Gmyp8"
ADMIN_ID = 5394084759

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def db_query(sql, params=(), fetchall=False, commit=False):
    with sqlite3.connect('chaihana_classic.db') as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if commit: conn.commit()
        if fetchall: return cursor.fetchall()
        return cursor.fetchone()

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS users 
                (user_id INTEGER, chat_id INTEGER, name TEXT, score INTEGER DEFAULT 0, last INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, chat_id))''', commit=True)
    db_query('''CREATE TABLE IF NOT EXISTS promos 
                (code TEXT PRIMARY KEY, bonus INTEGER, uses INTEGER)''', commit=True)

def get_user_rank(user_id, chat_id):
    results = db_query("SELECT user_id FROM users WHERE chat_id = ? ORDER BY score DESC", (chat_id,), fetchall=True)
    for index, row in enumerate(results, 1):
        if row[0] == user_id:
            return index
    return 1

# --- ОБРАБОТЧИКИ ---

@dp.message(F.text)
async def handle_text(msg: types.Message):
    text = msg.text.lower().strip()
    user_id = msg.from_user.id
    chat_id = msg.chat.id
    user_full_name = msg.from_user.full_name

    # КОМАНДА: ЧАЙХАНА
    if text == "чайхана":
        user = db_query("SELECT score, last FROM users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        now = int(time.time())
        
        if user and now - user[1] < 86400:
            return await msg.reply("Следующая попытка завтра!")

        # Рандом от -5 до 10 (исключая 0)
        change = random.choice([i for i in range(-5, 11) if i != 0])
        current_score = user[0] if user else 0
        new_score = current_score + change
        
        db_query("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)", 
                 (user_id, chat_id, user_full_name, new_score, now), commit=True)
        
        rank = get_user_rank(user_id, chat_id)
        word = "выросла" if change > 0 else "упала"
        
        # Тот самый формат ответа
        res_text = (
            f"{user_full_name}, твоя преданность чайхане {word} на {abs(change)} очков.\n"
            f"Теперь она равна {new_score} очков.\n"
            f"Ты занимаешь {rank} место в топе\n"
            f"Следующая попытка завтра!"
        )
        await msg.answer(res_text)

    # ТОП ЧАТА
    elif text in ["топ", "/top"]:
        top = db_query("SELECT name, score FROM users WHERE chat_id = ? ORDER BY score DESC LIMIT 10", (chat_id,), fetchall=True)
        if not top: return await msg.answer("Топ пуст.")
        res = "Топ чата:\n" + "\n".join([f"{i}. {n} — {s}" for i, (n, s) in enumerate(top, 1)])
        await msg.answer(res)

    # МИРОВОЙ ТОП
    elif text in ["мир", "/world", "глобал"]:
        top = db_query("SELECT name, SUM(score) as s FROM users GROUP BY user_id ORDER BY s DESC LIMIT 10", fetchall=True)
        res = "Мировой топ:\n" + "\n".join([f"{i}. {n} — {s}" for i, (n, s) in enumerate(top, 1)])
        await msg.answer(res)

    # ЮЗАТЬ ПРОМО
    elif text.startswith("юзать") or text.startswith("/use"):
        try:
            code = msg.text.split()[1]
            p = db_query("SELECT bonus, uses FROM promos WHERE code = ?", (code,))
            if p and p[1] > 0:
                db_query("UPDATE promos SET uses = uses - 1 WHERE code = ?", (code,), commit=True)
                curr = db_query("SELECT score, last FROM users WHERE user_id=? AND chat_id=?", (user_id, chat_id))
                score = (curr[0] if curr else 0) + p[0]
                db_query("INSERT OR REPLACE INTO users (user_id, chat_id, name, score, last) VALUES (?, ?, ?, ?, ?)",
                         (user_id, chat_id, user_full_name, score, curr[1] if curr else 0), commit=True)
                await msg.reply(f"Добавлено {p[0]} очков.")
            else:
                await msg.reply("Код не работает.")
        except: pass

    # СОЗДАНИЕ ПРОМО (АДМИН)
    elif text.startswith("промик") or text.startswith("/promo"):
        if user_id != ADMIN_ID: return
        try:
            _, code, bonus, uses = msg.text.split()
            db_query("INSERT INTO promos VALUES (?, ?, ?)", (code, int(bonus), int(uses)), commit=True)
            await msg.reply(f"Код {code} создан.")
        except: pass

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())