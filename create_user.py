import psycopg2
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()


def create_user(username, email, password):
    # パスワードをハッシュ化する
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)

    # DBに接続
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
    )
    cursor = conn.cursor()

    try:
        # DBに登録
        cursor.execute(
            """
        INSERT INTO users (username,email,password_hash)
        VALUES (%s,%s,%s)
        """,
            (username, email, password_hash.decode("utf-8")),
        )

        conn.commit()
        print(f"ユーザー作成成功:{username}({email})")

    except Exception as e:
        print(f"エラー:{e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    create_user("テスト三郎", "test3@example.com", "password333")
