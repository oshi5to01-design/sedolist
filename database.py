import os

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


# -----------------------------------------------
# データベース接続プールの作成
# -----------------------------------------------
@st.cache_resource
def init_db_pool():
    """
    コネクションプールを作成してキャッシュする。
    アプリ起動時に1回だけ実行され、あとは使い回される。
    """

    return psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
    )


def get_connection():
    """コネクションプールから接続を取得する"""
    db_pool = init_db_pool()
    return db_pool.getconn()


def release_connection(conn):
    """コネクションプールに接続を返却する"""
    if conn:
        db_pool = init_db_pool()
        db_pool.putconn(conn)


# -----------------------------------------------
# 在庫データ関連
# -----------------------------------------------
def load_items(user_id):
    """指定されたユーザーの在庫データをデータフレームで取得する"""
    conn = get_connection()
    try:
        query = "SELECT * FROM items WHERE user_id = %s ORDER BY id DESC;"
        df = pd.read_sql(query, conn, params=(user_id,))
        return df
    finally:
        release_connection(conn)


def register_item(user_id, name, price, shop, quantity, memo):
    """新しい商品をデータベースに登録する"""
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
    INSERT INTO items (user_id,name,price,shop,quantity,memo)
    VALUES (%s,%s,%s,%s,%s,%s)
    """

    try:
        cursor.execute(sql, (user_id, name, price, shop, quantity, memo))
        conn.commit()
        st.success(f"{name}を登録しました！")

        # load_items.clear()

    except Exception as e:
        conn.rollback()
        st.error(f"登録エラー:{e}")
    finally:
        cursor.close()
        release_connection(conn)


def update_item(item_id, col_name, new_value):
    """指定された商品の特定の項目(カラム)を更新する"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # numpyの型変更対策
        if hasattr(item_id, "item"):
            item_id = item_id.item()
        if hasattr(new_value, "item"):
            new_value = new_value.item()

        sql = f"UPDATE items SET {col_name} = %s WHERE id = %s"
        cursor.execute(sql, (new_value, item_id))
        conn.commit()

        # load_items.clear()

    except Exception as e:
        st.error(f"更新エラー:{e}")
    finally:
        cursor.close()
        release_connection(conn)


def delete_item(item_id):
    """指定された商品をデータベースから削除する"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # numpyの型変更対策
        if hasattr(item_id, "item"):
            item_id = item_id.item()

        cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
        conn.commit()

        # load_items.clear()

    except Exception as e:
        st.error(f"削除エラー:{e}")
    finally:
        cursor.close()
        release_connection(conn)


# -----------------------------------------------
# ユーザー情報更新関連
# -----------------------------------------------
def delete_user_account(user_id):
    """ユーザーアカウントを削除する(関連する在庫データも連鎖して削除される)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"退会処理エラー:{e}")
        return False
    finally:
        cursor.close()
        release_connection(conn)


def update_username(user_id, new_username):
    """ユーザーの表示名を更新する"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET username = %s WHERE id = %s", (new_username, user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"更新エラー:{e}")
        return False
    finally:
        cursor.close()
        release_connection(conn)


def get_user_email(user_id):
    """指定されたユーザーの現在のメールアドレスを取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else ""
    finally:
        cursor.close()
        release_connection(conn)


def update_email(user_id, new_email):
    """ユーザーのメールアドレスを更新する(重複チェック付き)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET email = %s WHERE id = %s", (new_email, user_id)
        )
        conn.commit()
        return True, "メールアドレスを変更しました！"
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False, "そのメールアドレスは既に使用されています"
    except Exception as e:
        conn.rollback()
        if "duplicate" in str(e):
            return False, "そのメールアドレスは既に使用されています"
        return False, f"更新エラー:{e}"
    finally:
        cursor.close()
        release_connection(conn)
