import secrets
from datetime import datetime, timedelta

import bcrypt
import psycopg2
import streamlit as st

from database import get_db


def check_login(email, password):
    """
    メールアドレスとパスワードでログイン認証を行う
    成功すれば(user_id,username)を返し、失敗すれば(None,None)を返す
    """
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id,username,password_hash FROM users WHERE email = %s", (email,)
        )
        user = cursor.fetchone()
        if user:
            user_id, username, password_hash = user
            # パスワード照合
            if bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
                return user_id, username
        return None, None
    except Exception as e:
        st.error(f"ログインエラー:{e}")
        return None, None
    finally:
        cursor.close()
        db.release_connection(conn)


def register_user(username, email, password):
    """
    新しいユーザーを登録する
    パスワードはハッシュ化して保存される
    戻り値:(成功したかどうかのTrue/False,メッセージ)
    """
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()

    # パスワードのハッシュ化
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    try:
        cursor.execute(
            "INSERT INTO users (username,email,password_hash) VALUES (%s,%s,%s)",
            (username, email, password_hash),
        )
        conn.commit()
        return True, "登録しました！"
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False, "そのメールアドレスは既に登録されています。"
    except Exception as e:
        conn.rollback()
        return False, f"登録エラー:{e}"
    finally:
        cursor.close()
        db.release_connection(conn)


def change_password(user_id, current_password, new_password):
    """
    現在のパスワードを確認し、合っていれば新しいパスワード(ハッシュ化済み)に更新する
    """
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if not result:
            return False, "ユーザーが見つかりません"

        current_hash_db = result[0]
        # 現在のパスワードチェック
        if not bcrypt.checkpw(
            current_password.encode("utf-8"), current_hash_db.encode("utf-8")
        ):
            return False, "現在のパスワードが間違っています"

        # 新しいパスワードをハッシュ化して更新
        salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(new_password.encode("utf-8"), salt).decode("utf-8")
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id)
        )
        conn.commit()
        return True, "パスワードを変更しました！"
    except Exception as e:
        return False, f"エラーが発生しました:{e}"
    finally:
        cursor.close()
        db.release_connection(conn)


def issue_reset_token(email):
    """
    パスワードリセット用のトークンを発行し、DBに保存する。
    開発用のため、リセットURLはターミナルに出力する。
    """
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()

    # ユーザー存在確認
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    if not cursor.fetchone():
        conn.close()
        return False

    # トークン生成
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=1)

    try:
        cursor.execute(
            "UPDATE users SET reset_token = %s,reset_token_expires_at = %s WHERE email = %s",
            (token, expires_at, email),
        )
        conn.commit()

        # URL生成と表示
        reset_url = f"http://localhost:8501/?token={token}"
        print("\n" + "=" * 50)
        print(f"【開発用メール】パスワードリセットURL:{reset_url}")
        print("=" * 50 + "\n")
        return True
    except Exception as e:
        st.error(f"トークン発行エラー:{e}")
        return False
    finally:
        cursor.close()
        db.release_connection(conn)


def verify_reset_token(token):
    """
    URLに含まれるトークンが有効(期限内かつDBに存在)かチェックする。
    """
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id,email FROM users WHERE reset_token = %s AND reset_token_expires_at > %s",
        (token, datetime.now()),
    )
    user = cursor.fetchone()
    cursor.close()
    db.release_connection(conn)
    return user


def reset_password(user_id, new_password):
    """
    パスワードリセット用:新しいパスワードを設定し、使用済みトークンを削除する。
    """
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(new_password.encode("utf-8"), salt).decode("utf-8")
    try:
        cursor.execute(
            "UPDATE users SET password_hash = %s,reset_token = NULL,reset_token_expires_at = NULL WHERE id = %s",
            (password_hash, user_id),
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"パスワード更新エラー:{e}")
        return False
    finally:
        cursor.close()
        db.release_connection(conn)
