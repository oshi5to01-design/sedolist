import secrets
from datetime import datetime, timedelta

import bcrypt
import streamlit as st

from database import SessionLocal, UserModel


def check_login(email, password):
    """
    メールアドレスとパスワードでログイン認証を行う
    成功すれば(user_id,username)を返し、失敗すれば(None,None)を返す
    """
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if user:
            # パスワード照合
            if bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            ):
                return user.id, user.username
        return None, None
    except Exception as e:
        st.error(f"ログインエラー:{e}")
        return None, None
    finally:
        db.close()


def register_user(username, email, password):
    """
    新しいユーザーを登録する
    パスワードはハッシュ化して保存される
    戻り値:(成功したかどうかのTrue/False,メッセージ)
    """
    db = SessionLocal()

    try:
        if db.query(UserModel).filter(UserModel.email == email).first():
            return False, "そのメールアドレスは既に登録されています。"

        # パスワードのハッシュ化
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

        # ユーザー作成
        new_user = UserModel(
            username=username, email=email, password_hash=password_hash
        )
        db.add(new_user)
        db.commit()
        return True, "登録しました！"
    except Exception as e:
        db.rollback()
        return False, f"登録エラー:{e}"
    finally:
        db.close()


def change_password(user_id, current_password, new_password):
    """
    現在のパスワードを確認し、合っていれば新しいパスワード(ハッシュ化済み)に更新する
    """
    db = SessionLocal()

    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            return False, "ユーザーが見つかりません"

        # 現在のパスワードチェック
        if not bcrypt.checkpw(
            current_password.encode("utf-8"), user.password_hash.encode("utf-8")
        ):
            return False, "現在のパスワードが間違っています"

        # 新しいパスワードをハッシュ化して更新
        salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(new_password.encode("utf-8"), salt).decode("utf-8")
        user.password_hash = new_hash
        db.commit()
        return True, "パスワードを変更しました！"
    except Exception as e:
        return False, f"エラーが発生しました:{e}"
    finally:
        db.close()


def issue_reset_token(email):
    """
    パスワードリセット用のトークンを発行し、DBに保存する。
    開発用のため、リセットURLはターミナルに出力する。
    """
    db = SessionLocal()

    try:
        # ユーザー存在確認
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if not user:
            return False

        # トークン生成
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)

        user.reset_token = token
        user.reset_token_expires_at = expires_at
        db.commit()

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
        db.close()


def verify_reset_token(token):
    """
    URLに含まれるトークンが有効(期限内かつDBに存在)かチェックする。
    """
    db = SessionLocal()
    try:
        user = (
            db.query(UserModel)
            .filter(
                UserModel.reset_token == token,
                UserModel.reset_token_expires_at > datetime.now(),
            )
            .first()
        )

        if user:
            return (user.id, user.email)
        return None
    finally:
        db.close()


def reset_password(user_id, new_password):
    """
    パスワードリセット用:新しいパスワードを設定し、使用済みトークンを削除する。
    """
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            salt = bcrypt.gensalt()
            user.password_hash = bcrypt.hashpw(
                new_password.encode("utf-8"), salt
            ).decode("utf-8")
            user.reset_token = None
            user.reset_token_expires_at = None
            db.commit()
            return True
        return False
    except Exception as e:
        st.error(f"パスワードリセットエラー:{e}")
        return False
    finally:
        db.close()
