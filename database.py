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
    inspect,
    text,
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

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    reset_token = Column(String, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class ItemModel(Base):
    """itemsテーブルのモデル"""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
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

    id = Column(Integer, primary_key=True)
    session_hash = Column(String, unique=True, index=True)  # ハッシュ化したトークン
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)


# -----------------------------------------------
# DatabaseManagerクラス
# -----------------------------------------------
class DatabaseManager:
    """データベース接続と操作を管理するクラス"""

    def __init__(self):
        """
        初期化:
            コネクションプールの作成とマイグレーション

        sessionsテーブルのスキーマ確認:
            開発中データベースの設計(カラム名)を変更した場合
            RenderのDBが古いままでエラーにならないよう起動時にスキーマをチェック
            旧カラム(session_id)があり、新カラム(session_hash)がない場合は再作成

        テーブルが存在しない場合は作成する
        """

        # sessionsテーブルのスキーマ確認
        inspector = inspect(engine)
        if inspector.has_table("sessions"):
            columns = [c["name"] for c in inspector.get_columns("sessions")]
            # 旧カラム(session_id)があり、新カラム(session_hash)がない場合は再作成
            if "session_id" in columns and "session_hash" not in columns:
                print("Old sessions table detected. Recreating...")
                try:
                    with engine.connect() as conn:
                        conn.execute(text("DROP TABLE sessions CASCADE"))
                        conn.commit()
                except Exception as e:
                    print(f"Migration error: {e}")

        # テーブルが存在しない場合は作成する
        Base.metadata.create_all(bind=engine)

    def get_db(self):
        """セッションを作成して返す"""
        return SessionLocal()

    # -----------------------------------------------
    # セッション管理関連
    # -----------------------------------------------
    def create_session(
        self, user_id: int, session_hash: str, expires_at: datetime
    ) -> None:
        """
        新しいセッションを登録する

        Args:
            user_id (int): ユーザーID
            session_hash (str): セッションハッシュ
            expires_at (datetime): セッションの有効期限

        Returns:
            None

        Notes:
            ログイン時にクッキーに保存する
        """
        db = self.get_db()
        try:
            new_session = SessionModel(
                user_id=user_id,
                session_hash=session_hash,
                expires_at=expires_at,
            )
            db.add(new_session)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"セッション作成エラー: {e}")
        finally:
            db.close()

    def get_user_by_session(self, session_hash: str) -> tuple[int, str] | None:
        """
        ハッシュ化されたトークンから有効なユーザーを取得する

        Args:
            session_hash (str): セッションハッシュ

        Returns:
            tuple[int, str] | None: ユーザーIDとユーザー名

        note:
            ログイン保持機能: セッションIDが合っているか,期限が切れてないか
            セッションテーブルとユーザーテーブルを紐付けて
            退会済みのユーザーが古いセッションでログインできないようにしている
            セッションにあるuser_idからuser情報を取得する
        """
        db = self.get_db()
        try:
            # 期限切れでないセッションを検索
            session = (
                db.query(SessionModel)
                .filter(
                    SessionModel.session_hash == session_hash,
                    SessionModel.expires_at > datetime.now(),
                )
                .first()
            )

            if session:
                user = (
                    db.query(UserModel).filter(UserModel.id == session.user_id).first()
                )
                if user:
                    return int(user.id), str(user.username)
            return None
        finally:
            db.close()

    def delete_session(self, session_hash: str) -> None:
        """
        セッションを削除する（ログアウト時）

        Args:
            session_hash (str): セッションハッシュ

        Returns:
            None
        """
        db = self.get_db()
        try:
            db.query(SessionModel).filter(
                SessionModel.session_hash == session_hash
            ).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def cleanup_expired_sessions(self) -> None:
        """
        有効期限切れのセッションを削除する

        Returns:
            None

        Notes:
            誰かのログインをトリガーにして削除するようにする
        """
        db = self.get_db()
        try:
            db.query(SessionModel).filter(
                SessionModel.expires_at < datetime.now()
            ).delete()
            db.commit()
        except Exception:
            pass
        finally:
            db.close()

    # -----------------------------------------------
    # 在庫データ関連
    # -----------------------------------------------
    def load_items(
        self,
        user_id: int,
        limit: int = 5,  # 本番では50にする予定
        last_id: int | None = None,
        search_query: str | None = None,
    ) -> pd.DataFrame:
        """
        指定されたユーザーの在庫データをデータフレームで取得する

        Args:
            user_id (int): ユーザーID

        Returns:
            pd.DataFrame: 指定されたユーザーの在庫データ

        Notes:
            ここだけStreamlitの表示速度優先でSQLAlchemyを使わずにSQL直書きし、
            pandasのDataFrameを返すようにしている
        """

        query = "SELECT * FROM items WHERE user_id = %s"
        params = [user_id]

        # 検索ワードがある場合
        if search_query:
            query += " AND name LIKE %s"
            # 部分一致検索
            params.append(f"%{search_query}%")  # type: ignore

        # カーソル(ページ送り)
        if last_id is not None:
            query += " AND id < %s"
            params.append(last_id)

        query += " ORDER BY id DESC LIMIT %s"
        params.append(limit)

        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params=tuple(params))

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
        """
        新しい商品をデータベースに登録する

        Args:
            user_id (int): ユーザーID
            name (str): 商品名
            price (int): 価格
            quantity (int): 在庫数
            shop (str | None, optional): 買った店舗名. Defaults to None.
            memo (str | None, optional): 備考. Defaults to None.

        Returns:
            None
        """
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
        """
        ゲストユーザー用にサンプルデータを一括登録する

        Args:
            user_id (int): ユーザーID

        Returns:
            None
        """
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
        """
        指定された商品の特定の項目(カラム)を更新する

        Args:
            item_id (int): 更新する商品のID
            col_name (str): 更新するカラム名
            new_value (Any): 更新する値

        Returns:
            None

        note:
            在庫の情報の更新・変更など
        """
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
        """
        指定された商品をデータベースから削除する

        Args:
            item_id (int): 削除する商品のID

        Returns:
            None

        note:
            売れたときなど
        """
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
        """
        ユーザーアカウントを削除する

        Args:
            user_id (int): ユーザーID

        Returns:
            bool: 削除成功/失敗

        note:
            CASCADEしているので、関連する在庫データも連鎖して削除される
        """
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
    """
    アプリ全体で一つだけのDatabaseManagerインスタンスを返す

    Streamlitの仕様上、リロードのたびにインスタンスが再生成されるのを防ぐため
    `@st.cache_resource` デコレータを使用してインスタンスをキャッシュ（メモリに常駐）させている
    これにより、コネクションプール（ThreadedConnectionPool）が不必要に増殖し
    DB接続数上限（Max Connections）に達するのを防いでいる
    """
    return DatabaseManager()
