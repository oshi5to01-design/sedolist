import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def init_database():
    print("初期化")

    # Dockerで立てたDBに接続
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # ================================================
        # 1.ユーザーテーブル(users)
        # ================================================
        print("usersテーブル作成中")

        cursor.execute("DROP TABLE IF EXISTS items;")
        cursor.execute("DROP TABLE IF EXISTS users;")

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            reset_token TEXT,
            reset_token_expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        )

        # =================================================
        # 2.在庫テーブル(items)
        # =================================================
        print("itemsテーブル作成中")
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            price INTEGER,
            shop TEXT,
            quantity INTEGER,
            memo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP            
        );
        """
        )

        print("完了！")

    except Exception as e:
        print(f"エラー:{e}")

    finally:
        if "conn" in locals() and conn:
            conn.close()


if __name__ == "__main__":
    init_database()
