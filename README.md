# せどりすと (Stock Manager) 📦

個人向けの在庫管理・商品登録支援アプリケーションです。
StreamlitによるシンプルなUIと、Google Gemini APIを活用した値札画像からの自動入力機能が特徴です。

## ✨ 主な機能

- **在庫一覧管理**: 登録済み商品を一覧表示。PC向け（表形式）とスマホ向け（カード形式）の表示切り替えが可能。
- **AI画像解析による自動登録**: 商品の値札やパッケージをカメラ撮影/アップロードすると、Gemini APIが商品名と価格を自動抽出して入力フォームに反映します。
- **ユーザー認証**: サインアップ、ログイン、ログアウト、パスワードリセット機能。
- **データ出力**: 在庫データのCSVダウンロード。
- **アカウント管理**: ユーザー名・メールアドレス・パスワードの変更、退会（データ全削除）。

## 🛠 技術スタック

- **Frontend/App Framework**: [Streamlit](https://streamlit.io/)
- **Backend Language**: Python 3.13+
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **AI**: Google Gemini API (`google-generativeai`)
- **Testing**: pytest

## 🚀 セットアップ手順

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd stock_manager
```

### 2. 環境構築
Python 3.13以上の環境が必要です。

```bash
# 仮想環境の作成と有効化 (推奨)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

### 3. 環境変数の設定
`.env` ファイルを作成し、以下の情報を記述してください。

```ini
# Database
DB_USER=your_db_user
DB_PASS=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_manager_db

# Gemini API (Google AI Studioで取得)
GEMINI_API_KEY=your_gemini_api_key
```

### 4. データベースの準備
PostgreSQLサーバーを起動し、上記 `.env` で指定した名前の空のデータベースを作成しておいてください。
テーブルはアプリ初回起動時に自動的に作成されます。

## ▶️ 実行方法

```bash
streamlit run app.py
```
ブラウザが起動し、`http://localhost:8501` でアプリにアクセスできます。

## 🧪 テスト実行

`pytest` を使用してユニットテストを実行できます。

```bash
# 全テストの実行
pytest

# 特定のファイルのテスト実行
pytest tests/test_auth.py
```

## 📁 ディレクトリ構成

- `app.py`: アプリケーションのエントリーポイント、UIロジック
- `auth.py`: 認証関連ロジック
- `database.py`: データベース接続、ORMモデル、CRUD操作
- `ai_logic.py`: Gemini API連携ロジック
- `tests/`: ユニットテストコード

## 📝 ライセンス

MIT License
