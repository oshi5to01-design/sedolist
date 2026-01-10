import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# testsディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# streamlitをモック
sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit.logger"] = MagicMock()

# databaseをモック
db_mock = MagicMock()
sys.modules["database"] = db_mock

import auth


class TestSessionManagement(unittest.TestCase):
    @patch("auth.get_db")
    @patch("auth.secrets")
    @patch("auth.hashlib")
    def test_create_session_token(self, mock_hashlib, mock_secrets, mock_get_db):
        # モックの準備
        mock_db_instance = MagicMock()
        mock_get_db.return_value = mock_db_instance

        mock_secrets.token_urlsafe.return_value = "dummy_token"

        mock_sha256 = MagicMock()
        mock_sha256.hexdigest.return_value = "hashed_token"
        mock_hashlib.sha256.return_value = mock_sha256

        # 実行
        token = auth.create_session_token(123)

        # 検証
        self.assertEqual(token, "dummy_token")
        mock_db_instance.create_session.assert_called_once()
        args = mock_db_instance.create_session.call_args[0]
        self.assertEqual(args[0], 123)
        self.assertEqual(args[1], "hashed_token")
        # 有効期限は現在から約30日後。厳密な時刻の一致を確認するのは難しいため、型の確認を行う。
        self.assertIsInstance(args[2], datetime)

    @patch("auth.get_db")
    @patch("auth.hashlib")
    def test_validate_session_token_valid(self, mock_hashlib, mock_get_db):
        # モックの準備
        mock_db_instance = MagicMock()
        mock_get_db.return_value = mock_db_instance

        mock_sha256 = MagicMock()
        mock_sha256.hexdigest.return_value = "hashed_token"
        mock_hashlib.sha256.return_value = mock_sha256

        mock_db_instance.get_user_by_session.return_value = (123, "testuser")

        # 実行
        result = auth.validate_session_token("valid_token")

        # 検証
        self.assertEqual(result, (123, "testuser"))
        mock_db_instance.get_user_by_session.assert_called_once_with("hashed_token")

    @patch("auth.get_db")
    def test_validate_session_token_none(self, mock_get_db):
        result = auth.validate_session_token(None)
        self.assertEqual(result, (None, None))

    @patch("auth.get_db")
    @patch("auth.hashlib")
    def test_revoke_session_token(self, mock_hashlib, mock_get_db):
        # モックの準備
        mock_db_instance = MagicMock()
        mock_get_db.return_value = mock_db_instance

        mock_sha256 = MagicMock()
        mock_sha256.hexdigest.return_value = "hashed_token"
        mock_hashlib.sha256.return_value = mock_sha256

        # 実行
        auth.revoke_session_token("token_to_revoke")

        # 検証
        mock_db_instance.delete_session.assert_called_once_with("hashed_token")


if __name__ == "__main__":
    unittest.main()
