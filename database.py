import os
from datetime import datetime
from typing import Any

import pandas as pd
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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


# -----------------------------------------------
# SQLAlchemyの設定(ORM)
# -----------------------------------------------
# データベースURLの構築
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
# エンジンの作成
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
# セッションの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 親クラス
Base: Any = declarative_base()


# -----------------------------------------------
# モデル定義(テーブルの設計図)
# -----------------------------------------------
class UserModel(Base):
    """usersテーブルのモデル"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
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

    def get_db(self):
        """セッションを作成して返す"""
        return SessionLocal()

    # -----------------------------------------------
    # 在庫データ関連
    # -----------------------------------------------
    def load_items(self, user_id: int) -> pd.DataFrame:
        """指定されたユーザーの在庫データをデータフレームで取得する"""

        query = "SELECT * FROM items WHERE user_id = %s ORDER BY id DESC;"

        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params=(user_id,))

        return df

    def register_item(
        self,
        user_id: int,
        name: str,
        price: int,
        quantity: int,
        shop: str | None = None,
        memo: str | None = None,
    ) -> None:
        """新しい商品をデータベースに登録する"""
        db = self.get_db()
        try:
            new_item = ItemModel(
                user_id=user_id,
                name=name,
                price=price,
                shop=shop,
                quantity=quantity,
                memo=memo,
            )
            db.add(new_item)
            db.commit()
            st.success(f"「{name}」を登録しました！")
        except Exception as e:
            db.rollback()
            st.error(f"登録エラー:{e}")
        finally:
            db.close()

    # ---------------------------------------------
    # サンプルデータ作成 (ゲスト用)
    # ---------------------------------------------
    def create_sample_items(self, user_id: int) -> None:
        """ゲストユーザー用にサンプルデータを一括登録する"""
        db = self.get_db()

        # サンプルデータのリスト
        samples = [
            {
                "name": "ゲーミングマウス G502",
                "price": 5800,
                "shop": "Amazon",
                "quantity": 3,
                "memo": "人気商品。セール時に確保。",
            },
            {
                "name": "メカニカルキーボード 赤軸",
                "price": 12000,
                "shop": "楽天",
                "quantity": 1,
                "memo": "箱に少し傷あり。",
            },
            {
                "name": "USB-C ハブ 7-in-1",
                "price": 3500,
                "shop": "家電量販店A",
                "quantity": 5,
                "memo": "",
            },
            {
                "name": "ノイズキャンセリングヘッドホン",
                "price": 24000,
                "shop": "Amazon",
                "quantity": 2,
                "memo": "ブラックフライデー仕入れ",
            },
            {
                "name": "スマホスタンド (アルミ)",
                "price": 1500,
                "shop": "100均一(高額枠)",
                "quantity": 10,
                "memo": "回転率よし",
            },
            {
                "name": "4Kモニター 27インチ",
                "price": 32000,
                "shop": "中古PCショップ",
                "quantity": 1,
                "memo": "ドット抜けなし確認済み",
            },
            {
                "name": "HDMIケーブル 2m",
                "price": 800,
                "shop": "Amazon",
                "quantity": 20,
                "memo": "ついで買い狙い",
            },
            {
                "name": "Webカメラ 1080p",
                "price": 4500,
                "shop": "メルカリ",
                "quantity": 0,
                "memo": "売り切れ。再入荷待ち。",
            },
            {
                "name": "デスクマット (大型)",
                "price": 2200,
                "shop": "AliExpress",
                "quantity": 4,
                "memo": "到着まで2週間かかった",
            },
            {
                "name": "LEDデスクライト",
                "price": 3800,
                "shop": "IKEA",
                "quantity": 2,
                "memo": "",
            },
        ]

        try:
            for item in samples:
                new_item = ItemModel(
                    user_id=user_id,
                    name=item["name"],
                    price=item["price"],
                    shop=item["shop"],
                    quantity=item["quantity"],
                    memo=item["memo"],
                )
                db.add(new_item)

            db.commit()

        except Exception as e:
            db.rollback()
            print(f"サンプルデータ作成エラー: {e}")
        finally:
            db.close()

    def update_item(self, item_id: int, col_name: str, new_value: Any) -> None:
        """指定された商品の特定の項目(カラム)を更新する"""
        db = self.get_db()
        try:
            # numpyの型変更対策
            if hasattr(new_value, "item"):
                new_value = new_value.item()
            if hasattr(item_id, "item"):
                item_id = item_id.item()

            item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
            if item:
                setattr(item, col_name, new_value)
                db.commit()

        except Exception as e:
            db.rollback()
            st.error(f"更新エラー:{e}")
        finally:
            db.close()

    def delete_item(self, item_id: int) -> None:
        """指定された商品をデータベースから削除する"""
        db = self.get_db()
        try:
            # numpyの型変更対策
            if hasattr(item_id, "item"):
                item_id = item_id.item()

            db.query(ItemModel).filter(ItemModel.id == item_id).delete()
            db.commit()

        except Exception as e:
            db.rollback()
            st.error(f"削除エラー:{e}")
        finally:
            db.close()

    # -----------------------------------------------
    # ユーザー情報更新関連
    # -----------------------------------------------
    def delete_user_account(self, user_id: int) -> bool:
        """ユーザーアカウントを削除する(関連する在庫データも連鎖して削除される)"""
        db = self.get_db()
        try:
            db.query(UserModel).filter(UserModel.id == user_id).delete()
            db.commit()
            return True
        except Exception as e:
            st.error(f"退会処理エラー:{e}")
            return False
        finally:
            db.close()

    def update_username(self, user_id: int, new_username: str) -> bool:
        """ユーザーの表示名を更新する"""
        db = self.get_db()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if user:
                user.username = new_username
                db.commit()
                return True
            return False
        except Exception as e:
            st.error(f"更新エラー:{e}")
            return False
        finally:
            db.close()

    def get_user_email(self, user_id: int) -> str:
        """指定されたユーザーの現在のメールアドレスを取得する"""
        db = self.get_db()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            return user.email if user else ""
        finally:
            db.close()

    def update_email(self, user_id: int, new_email: str) -> tuple[bool, str]:
        """ユーザーのメールアドレスを更新する"""
        db = self.get_db()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if user:
                user.email = new_email
                db.commit()
                return True, "メールアドレスを更新しました"
            return False, "ユーザーが見つかりません"

        except IntegrityError:
            db.rollback()
            return False, "そのメールアドレスは既に使用されています"

        except Exception as e:
            db.rollback()
            return False, f"更新エラー:{e}"
        finally:
            db.close()


# -----------------------------------------------
# シングルトン(一つだけ作る)管理用関数
# -----------------------------------------------
@st.cache_resource
def get_db():
    """アプリ全体で一つだけのDatabaseManagerインスタンスを返す"""
    return DatabaseManager()
