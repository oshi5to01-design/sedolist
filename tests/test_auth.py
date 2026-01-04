from unittest.mock import patch

import bcrypt

import auth
from database import UserModel


def test_register_user_success(db_session):
    """正常なユーザー登録テスト"""
    # SessionLocalをmockして、テスト用のdb_sessionを返すようにする
    with patch("auth.SessionLocal", return_value=db_session):
        success, msg = auth.register_user("testuser", "test@example.com", "password123")

        assert success is True
        assert msg == "登録しました！"

        # DBに保存されているか確認
        user = db_session.query(UserModel).filter_by(email="test@example.com").first()
        assert user is not None
        assert user.username == "testuser"
        # パスワードがハッシュ化されているか
        assert bcrypt.checkpw("password123".encode(), user.password_hash.encode())


def test_register_user_duplicate_email(db_session):
    """重複メールアドレス登録テスト"""
    with patch("auth.SessionLocal", return_value=db_session):
        # 1人目
        auth.register_user("user1", "dup@example.com", "pass1")

        # 2人目（同じメール）
        success, msg = auth.register_user("user2", "dup@example.com", "pass2")

        assert success is False
        assert msg == "そのメールアドレスは既に登録されています。"


def test_check_login_success(db_session):
    """ログイン成功テスト"""
    with patch("auth.SessionLocal", return_value=db_session):
        # ユーザー準備
        auth.register_user("login_user", "login@example.com", "correct_pass")

        # 正しいパスワード
        user_id, username = auth.check_login("login@example.com", "correct_pass")

        assert user_id is not None
        assert username == "login_user"


def test_check_login_failure(db_session):
    """ログイン失敗テスト"""
    with patch("auth.SessionLocal", return_value=db_session):
        # ユーザー準備
        auth.register_user("login_user2", "fail@example.com", "pass")

        # 間違ったパスワード
        user_id, username = auth.check_login("fail@example.com", "wrong_pass")
        assert user_id is None
        assert username is None

        # 存在しないユーザー
        user_id, username = auth.check_login("nobody@example.com", "pass")
        assert user_id is None
        assert username is None


def test_change_password(db_session):
    """パスワード変更テスト"""
    with patch("auth.SessionLocal", return_value=db_session):
        # ユーザー準備
        auth.register_user("change_pw_user", "change@example.com", "old_pass")
        user = db_session.query(UserModel).filter_by(email="change@example.com").first()
        user_id = user.id

        # パスワード変更実行
        success, msg = auth.change_password(user_id, "old_pass", "new_pass")
        assert success is True

        # 新しいパスワードでログインできるか（ハッシュが変わっているか確認）
        # DB再取得 (一度closeされているため、expireではなく新規クエリを行う)
        updated_user = db_session.query(UserModel).filter_by(id=user_id).first()
        assert bcrypt.checkpw("new_pass".encode(), updated_user.password_hash.encode())
        assert not bcrypt.checkpw(
            "old_pass".encode(), updated_user.password_hash.encode()
        )
