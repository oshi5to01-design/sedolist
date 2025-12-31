import os
from datetime import datetime

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


# -----------------------------------------------
# SQLAlchemyの設定(ORM)
# -----------------------------------------------
# データベースURLの構築
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
# エンジンの作成
engine = create_engine(DATABASE_URL)
# セッションの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 親クラス
Base = declarative_base()


# -----------------------------------------------
# モデル定義(テーブルの設計図)
# -----------------------------------------------
class UserModel(Base):
    """usersテーブルのモデル"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    reset_token = Column(String, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class ItemModel(Base):
    """itemsテーブルのモデル"""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    price = Column(Integer)
    shop = Column(String)
    quantity = Column(Integer)
    memo = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class SessionModel(Base):
    """sessionsテーブルのモデル"""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)


# -----------------------------------------------
# DatabaseManagerクラス
# -----------------------------------------------
class DatabaseManager:
    """データベース接続と操作を管理するクラス"""

    def __init__(self):
        """初期化: コネクションプールの作成"""

        # テーブルが存在しない場合は作成する
        Base.metadata.create_all(bind=engine)

        self.pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
        )

    def get_connection(self):
        """コネクションプールから接続を取得する"""
        return self.pool.getconn()

    def release_connection(self, conn):
        """コネクションプールに接続を返却する"""
        if conn:
            self.pool.putconn(conn)

    # -----------------------------------------------
    # 在庫データ関連
    # -----------------------------------------------
    def load_items(self, user_id):
        """指定されたユーザーの在庫データをデータフレームで取得する"""
        conn = self.get_connection()
        try:
            query = "SELECT * FROM items WHERE user_id = %s ORDER BY id DESC;"
            df = pd.read_sql(query, conn, params=(user_id,))
            return df
        finally:
            self.release_connection(conn)

    def register_item(self, user_id, name, price, shop, quantity, memo):
        """新しい商品をデータベースに登録する"""
        conn = self.get_connection()
        cursor = conn.cursor()
        sql = """
        INSERT INTO items (user_id,name,price,shop,quantity,memo)
        VALUES (%s,%s,%s,%s,%s,%s)
        """

        try:
            cursor.execute(sql, (user_id, name, price, shop, quantity, memo))
            conn.commit()
            st.success(f"{name}を登録しました！")

        except Exception as e:
            conn.rollback()
            st.error(f"登録エラー:{e}")
        finally:
            cursor.close()
            self.release_connection(conn)

    def update_item(self, item_id, col_name, new_value):
        """指定された商品の特定の項目(カラム)を更新する"""
        conn = self.get_connection()
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

        except Exception as e:
            st.error(f"更新エラー:{e}")
        finally:
            cursor.close()
            self.release_connection(conn)

    def delete_item(self, item_id):
        """指定された商品をデータベースから削除する"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # numpyの型変更対策
            if hasattr(item_id, "item"):
                item_id = item_id.item()

            cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
            conn.commit()

        except Exception as e:
            st.error(f"削除エラー:{e}")
        finally:
            cursor.close()
            self.release_connection(conn)

    # -----------------------------------------------
    # ユーザー情報更新関連
    # -----------------------------------------------
    def delete_user_account(self, user_id):
        """ユーザーアカウントを削除する(関連する在庫データも連鎖して削除される)"""
        conn = self.get_connection()
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
            self.release_connection(conn)

    def update_username(self, user_id, new_username):
        """ユーザーの表示名を更新する"""
        conn = self.get_connection()
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
            self.release_connection(conn)

    def get_user_email(self, user_id):
        """指定されたユーザーの現在のメールアドレスを取得する"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else ""
        finally:
            cursor.close()
            self.release_connection(conn)

    def update_email(self, user_id, new_email):
        """ユーザーのメールアドレスを更新する(重複チェック付き)"""
        conn = self.get_connection()
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
            self.release_connection(conn)

    # -----------------------------------------------
    # セッション管理メソッド(SQLAlchemyを使用)
    # -----------------------------------------------
    def create_session(self, user_id):
        """新しいセッションを作成し、セッションIDを返す"""
        db = SessionLocal()
        try:
            token = secrets.token_urlsafe(32)
            expires = datetime.now() + timedelta(days=30)  # 30日間有効

            # オブジェクトとしてデータを作成
            new_session = SessionModel(
                session_id=token, user_id=user_id, expires_at=expires
            )
            db.add(new_session)
            db.commit()
            return token, expires
        except Exception as e:
            print(f"セッション作成エラー:{e}")
            return None, None
        finally:
            db.close()

    def get_user_by_session(self, token):
        """セッションIDからユーザーIDを取得する"""
        db = SessionLocal()
        try:
            session = (
                db.query(SessionModel)
                .filter(
                    SessionModel.session_id == token,
                    SessionModel.expires_at > datetime.now(),
                )
                .first()
            )

            if session:
                return session.user_id
            return None
        finally:
            db.close()

    def delete_session(self, token):
        """ログアウト時にセッションを削除する"""
        db = SessionLocal()
        try:
            db.query(SessionModel).filter(SessionModel.session_id == token).delete()
            db.commit()
        finally:
            db.close()


# -----------------------------------------------
# シングルトン(一つだけ作る)管理用関数
# -----------------------------------------------
@st.cache_resource
def get_db():
    """アプリ全体で一つだけのDatabaseManagerインスタンスを返す"""
    return DatabaseManager()
