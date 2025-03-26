import sqlite3
import time
import os
from datetime import datetime

class Database:
    def __init__(self, db_file):
        # Создаем папку для базы, если её ещё нет
        folder = os.path.dirname(db_file)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()
        self.migrate_tables()  # Миграция для таблицы users
        self.migrate_reactions_table()  # Миграция для таблицы reactions

    def create_tables(self):
        # Таблица пользователей
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                nickname TEXT,
                signup TEXT,
                time_sub INTEGER DEFAULT 0,
                wallet TEXT DEFAULT '0₽',
                partner_account TEXT DEFAULT '0₽',
                subscription TEXT DEFAULT '',
                query_limit TEXT DEFAULT '100',
                photos INTEGER DEFAULT 0,
                cars INTEGER DEFAULT 0,
                emails INTEGER DEFAULT 0,
                phone_numbers INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                ratings INTEGER DEFAULT 0
            )
        """)
        # Таблица реакций
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reactions (
                query TEXT,
                user_id INTEGER,
                reaction TEXT,
                PRIMARY KEY (query, user_id)
            )
        """)
        # Таблица поисковых запросов
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT,
                timestamp INTEGER
            )
        """)
        self.connection.commit()

    def migrate_tables(self):
        self.cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in self.cursor.fetchall()]
        if 'views' not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN views INTEGER DEFAULT 0")
        if 'ratings' not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN ratings INTEGER DEFAULT 0")
        self.connection.commit()

    def migrate_reactions_table(self):
        self.cursor.execute("PRAGMA table_info(reactions)")
        columns = [info[1] for info in self.cursor.fetchall()]
        if "query" not in columns:
            self.cursor.execute("DROP TABLE IF EXISTS reactions")
            self.connection.commit()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS reactions (
                    query TEXT,
                    user_id INTEGER,
                    reaction TEXT,
                    PRIMARY KEY (query, user_id)
                )
            """)
            self.connection.commit()

    def add_user(self, user_id):
        with self.connection:
            self.cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, signup) VALUES (?, ?)",
                (user_id, datetime.now().strftime("%d.%m.%Y"))
            )
        self.connection.commit()

    def user_exists(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)).fetchone()
            return result is not None

    def set_nickname(self, user_id, nickname):
        with self.connection:
            self.cursor.execute("UPDATE users SET nickname=? WHERE user_id=?", (nickname, user_id))
        self.connection.commit()

    def get_signup(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT signup FROM users WHERE user_id=?", (user_id,)).fetchone()
            return result[0] if result else None

    def set_signup(self, user_id, signup):
        with self.connection:
            self.cursor.execute("UPDATE users SET signup=? WHERE user_id=?", (signup, user_id))
        self.connection.commit()

    def get_nickname(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT nickname FROM users WHERE user_id=?", (user_id,)).fetchone()
            return result[0] if result else None

    def set_time_sub(self, user_id, time_sub):
        with self.connection:
            current_time_sub = self.get_time_sub(user_id) or int(time.time())
            new_time_sub = int(current_time_sub) + time_sub
            self.cursor.execute("UPDATE users SET time_sub=? WHERE user_id=?", (new_time_sub, user_id))
        self.connection.commit()

    def get_time_sub(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT time_sub FROM users WHERE user_id=?", (user_id,)).fetchone()
            return int(result[0]) if result else 0

    def get_sub_status(self, user_id):
        time_sub = self.get_time_sub(user_id)
        return time_sub > int(time.time())

    def get_wallet(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT wallet FROM users WHERE user_id=?", (user_id,)).fetchone()
            return result[0] if result else "0₽"

    def set_wallet(self, user_id, wallet):
        with self.connection:
            self.cursor.execute("UPDATE users SET wallet=? WHERE user_id=?", (wallet, user_id))
        self.connection.commit()

    def get_partner_account(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT partner_account FROM users WHERE user_id=?", (user_id,)).fetchone()
            return result[0] if result else "0₽"

    def set_partner_account(self, user_id, partner_account):
        with self.connection:
            self.cursor.execute("UPDATE users SET partner_account=? WHERE user_id=?", (partner_account, user_id))
        self.connection.commit()

    def get_subscription(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT subscription FROM users WHERE user_id=?", (user_id,)).fetchone()
            return result[0] if result else ""

    def set_subscription(self, user_id, subscription):
        with self.connection:
            self.cursor.execute("UPDATE users SET subscription=? WHERE user_id=?", (subscription, user_id))
        self.connection.commit()

    def get_query_limit(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT query_limit FROM users WHERE user_id=?", (user_id,)).fetchone()
            return result[0] if result else "100"

    def set_query_limit(self, user_id, query_limit):
        with self.connection:
            self.cursor.execute("UPDATE users SET query_limit=? WHERE user_id=?", (query_limit, user_id))
        self.connection.commit()

    def update_stats(self, user_id, photos=0, cars=0, emails=0, phone_numbers=0, views=0, ratings=0):
        with self.connection:
            self.cursor.execute("""
                UPDATE users 
                SET photos = photos + ?, 
                    cars = cars + ?, 
                    emails = emails + ?, 
                    phone_numbers = phone_numbers + ?,
                    views = views + ?,
                    ratings = ratings + ?
                WHERE user_id = ?
            """, (photos, cars, emails, phone_numbers, views, ratings, user_id))
        self.connection.commit()

    def reaction_exists(self, query, user_id):
        with self.connection:
            result = self.cursor.execute(
                "SELECT 1 FROM reactions WHERE query=? AND user_id=?",
                (query, user_id)
            ).fetchone()
            return result is not None

    def add_reaction(self, query, user_id, reaction):
        with self.connection:
            self.cursor.execute(
                "INSERT INTO reactions (query, user_id, reaction) VALUES (?, ?, ?)",
                (query, user_id, reaction)
            )
        self.connection.commit()

    def get_reaction_counts(self, query):
        self.cursor.execute("""
            SELECT reaction, COUNT(*) FROM reactions 
            WHERE query = ?
            GROUP BY reaction
        """, (query,))
        results = self.cursor.fetchall()
        counts = {"up": 0, "down": 0}
        for reaction, count in results:
            counts[reaction] = count
        return counts

    def log_search(self, user_id, query):
        with self.connection:
            self.cursor.execute('''
                INSERT INTO searches (user_id, query, timestamp)
                VALUES (?, ?, strftime('%s', 'now'))
            ''', (user_id, query))
            # Обновляем статистику запросов на основании содержимого запроса
            if query.isdigit() and len(query) in (10, 11, 15):
                # Предполагаем, что это номер телефона
                self.cursor.execute("UPDATE users SET phone_numbers = phone_numbers + 1 WHERE user_id = ?", (user_id,))
            elif "@" in query:
                # Предполагаем, что это email
                self.cursor.execute("UPDATE users SET emails = emails + 1 WHERE user_id = ?", (user_id,))
            # Можно добавить дополнительные условия для фото, авто и т.д.
        self.connection.commit()

    def count_unique_searches(self, query):
        with self.connection:
            result = self.cursor.execute('''
                SELECT COUNT(DISTINCT user_id) FROM searches WHERE query = ?
            ''', (query,)).fetchone()
            return result[0] if result else 0
