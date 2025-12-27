import streamlit as st
import psycopg2
import pandas as pd
import bcrypt
import google.generativeai as genai
from PIL import Image
import json
import os
from dotenv import load_dotenv
import secrets
from datetime import datetime, timedelta


# -----------------------------------------------
# 認証関連の関数
# -----------------------------------------------
def check_login(email, password):
    """メアドとパスワードでログイン認証する"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # メアドでユーザーを探す
        cursor.execute(
            "SELECT id,username,password_hash FROM users WHERE email = %s", (email,)
        )
        user = cursor.fetchone()

        if user:
            user_id, username, password_hash = user
            # パスワードが合っているか検証
            if bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
                return user_id, username
        return None, None

    except Exception as e:
        st.error(f"ログインエラー:{e}")
        return None, None

    finally:
        conn.close()


# -----------------------------------------------
# ユーザー新規登録関数
# -----------------------------------------------
def register_user(username, email, password):
    """新しいユーザーを登録する"""
    conn = get_connection()
    cursor = conn.cursor()

    # パスワードのハッシュ化
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    try:
        cursor.excute(
            """INSERT INTO users (username,email,password_hash) VALUES (%s,%s,%s)""",
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
        conn.close()


# -----------------------------------------------
# パスワード変更関数
# -----------------------------------------------
def change_password(user_id, current_password, new_password):
    """
    現在のパスワードを確認し、合っていれば新しいパスワードに更新する
    戻り値:(成功したかどうかのTrue/False,メッセージ)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # DBから現在のハッシュを取得
        cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            return False, "ユーザーが見つかりません"

        current_hash_db = result[0]

        # 現在のパスワードが正しいかチェック
        if not bcrypt.checkpw(
            current_password.encode("utf-8"), current_hash_db.encode("utf-8")
        ):
            return False, "現在のパスワードが間違っています"

        # 新しいパスワードをハッシュ化
        salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(new_password.encode("utf-8"), salt).decode("utf-8")

        # DB更新
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id)
        )
        conn.commit()

        return True, "パスワードを変更しました！"

    except Exception as e:
        return False, f"エラーが発生しました:{e}"
    finally:
        conn.close()


# ----------------------------------------------
# ユーザー名変更関数
# ----------------------------------------------
def update_username(user_id, new_username):
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
        conn.close()


# ----------------------------------------------
# 現在のメールアドレスを取得する関数
# ----------------------------------------------
def get_user_email(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else ""
    finally:
        conn.close()


# ----------------------------------------------
# メールアドレス変更関数
# ----------------------------------------------
def update_email(user_id, new_email):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET email = %s WHERE id = %s", (new_email, user_id)
        )
        conn.commit()
        return True, "メールアドレスを変更しました！"
    except psycopg2.errors.UniqueViolation:  # 重複エラーをキャッチ
        conn.rollback()
        return False, "そのメールアドレスは既に使用されています"
    except Exception as e:
        conn.rollback()
        # エラーの中に"duplicate"が含まれていたら重複とみなす
        if "duplicate" in str(e):
            return False, "そのメールアドレスは既に使用されています。"
        return False, f"更新エラー:{e}"
    finally:
        conn.close()


# ----------------------------------------------
# パスワードリセット関連の関数
# ----------------------------------------------
def issue_reset_token(email):
    """トークンを発行してDBに保存し、URLをターミナルに表示する"""
    conn = get_connection()
    cursor = conn.cursor()

    # そのメアドのユーザーがいるか確認
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return False

    # トークンを作る
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=1)

    try:
        # DBにトークンと期限を書き込む
        cursor.execute(
            """
            UPDATE users
            SET reset_token = %s,reset_token_expires_at = %s
            WHERE email = %s
            """,
            (token, expires_at, email),
        )
        conn.commit()

        # メールの代わりにターミナルに表示
        reset_url = f"http://localhost:8501/?token={token}"

        print("\n" + "=" * 50)
        print(f"【開発用メール】パスワードリセットURL:{reset_url}")
        print("=" * 50 + "\n")

        return True

    except Exception as e:
        st.error(f"トークン発行エラー:{e}")
        return False
    finally:
        conn.close()


def verify_reset_token(token):
    """トークンが有効かチェックする"""
    conn = get_connection()
    cursor = conn.cursor()

    # トークンが一致し、かつ期限切れしていないユーザーを探す
    cursor.execute(
        """SELECT id,email FROM users 
        WHERE reset_token = %s AND reset_token_expires_at > %s""",
        (token, datetime.now()),
    )

    user = cursor.fetchone()
    conn.close()
    return user


def reset_password(user_id, new_password):
    """新しいパスワードを設定し、トークンを消す"""
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(new_password.encode("utf-8"), salt).decode("utf-8")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # パスワードを更新し、トークン類はNULLにして消す
        cursor.execute(
            """UPDATE users 
            SET password_hash = %s,reset_token = NULL,reset_token_expires_at = NULL 
            WHERE id = %s""",
            (password_hash, user_id),
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"パスワード更新エラー:{e}")
        return False
    finally:
        conn.close()


# ----------------------------------------------
# データベースに接続する関数
# ----------------------------------------------
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
    )


# ----------------------------------------------
# 入力フォームをクリアする関数
# ----------------------------------------------
def clear_form_state():
    st.session_state.input_name = ""
    st.session_state.input_price = 0
    st.session_state.input_quantity = 1
    st.session_state.input_shop = ""
    st.session_state.input_memo = ""


# ---------------------------------------------
# データを読み込む関数
# ---------------------------------------------
def load_items(user_id):
    conn = get_connection()
    # pandasを使ってSQLの結果をそのまま表データ(DataFrame)にする
    query = "SELECT * FROM items WHERE user_id = %s ORDER BY id DESC;"
    df = pd.read_sql(query, conn, params=(user_id,))
    conn.close()
    return df


# ------------------------------------------------
# データの保存関数(INSERT)
# ------------------------------------------------
def register_item(user_id, name, price, shop, quantity, memo):
    conn = get_connection()
    cursor = conn.cursor()

    # SQLでデータを挿入
    # user_idはとりあえず1
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
        conn.close()


# ---------------------------------------------------
# データの更新関数
# ---------------------------------------------------
def update_item(item_id, col_name, new_value):
    conn = get_connection()
    cursor = conn.cursor()
    try:
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
        conn.close()


# ---------------------------------------------------
# データの削除関数
# ---------------------------------------------------
def delete_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if hasattr(item_id, "item"):
            item_id = item_id.item()

        cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
        conn.commit()
    except Exception as e:
        st.error(f"削除エラー:{e}")
    finally:
        conn.close()


# ---------------------------------------------------
# ユーザー削除関数(退会)
# ---------------------------------------------------
def delete_user_account(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # ON DELETE CASCADEがあるので、usersを消せばitemsも勝手に消える
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"退会処理エラー:{e}")
        return False
    finally:
        conn.close()


# .env読み込み
load_dotenv()

# Geminiの設定
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def analyze_image_with_gemini(uploaded_file):
    """
    画像をGeminiに渡して、商品名と価格を抽出する関数
    """
    try:
        # 画像を読み込む
        image = Image.open(uploaded_file)

        # モデル（gemini-1.5-flash）
        model = genai.GenerativeModel("models/gemini-flash-latest")

        # プロンプト
        prompt = """
        この画像を分析して、いかの情報を抽出してください。

        1.商品名(name):パッケージや値札から読み取れる具体的な商品名
        2.価格(price):値札に書かれている価格(数字のみ、円マークやカンマは除く)

        出力は必ずいかのJSON形式のみにしてください。余計な文章は不要です。
        {
            "name":"商品名",
            "price":1000
        }
        """

        # AIに聞く
        with st.spinner("AIが画像を解析中"):
            response = model.generate_content([prompt, image])
            text = response.text

            # JSON形式の文字列を探して取り出す
            clean_text = text.replace("```json", "").replace("```", "").strip()

            # 辞書データに変換
            result = json.loads(clean_text)
            return result

    except Exception as e:
        st.error(f"AI解析エラー:{e}")
        return None


# ---------------------------------------------
# 画面の表示
# ---------------------------------------------

# セッションステートの初期化（ログイン状態管理）
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""

# URLからトークンを取得
query_params = st.query_params
reset_token = query_params.get("token", None)

# パスワード再設定モード（URLにトークンがある場合）
if reset_token:
    st.title("パスワード再設定")

    # トークンが有効かチェック
    user = verify_reset_token(reset_token)

    if user:
        # user=(id,email)
        st.success(f"本人確認が完了しました。\n対象アカウント:{user[1]}")

        with st.form("new_password_form"):
            new_pw = st.text_input("新しいパスワード", type="password")
            submitted = st.form_submit_button("変更する")

            if submitted:
                if not new_pw:
                    st.warning("パスワードを入力してください")
                else:
                    # パスワード更新実行
                    if reset_password(user[0], new_pw):
                        st.success("パスワードを変更しました！")
                        st.info("ログイン画面に戻ります")

                        # URLのトークンを消してリロード
                        import time

                        time.sleep(2)
                        st.query_params.clear()
                        st.rerun()
    else:
        st.error("このリンクは無効か、有効期限が切れています。")
        if st.button("ログイン画面へ戻る"):
            st.query_params.clear()
            st.rerun()

    # ここで処理を止める
    st.stop()

# ログインしてない場合
if not st.session_state.logged_in:
    st.title("ログイン")

    # タブでログインとリセット申請を切り替える
    tab1, tab2, tab3 = st.tabs(["ログイン", "新規登録", "パスワードを忘れた場合"])

    # いつものログイン
    with tab1:
        with st.form("login_form"):
            email = st.text_input("メールアドレス")

            # パスワード表示スイッチ
            show_password = st.checkbox("パスワードを表示して入力する")
            if show_password:
                password = st.text_input("パスワード", key="pw_visible")
            else:
                password = st.text_input("パスワード", type="password", key="pw_hidden")

            submitted = st.form_submit_button("ログイン")

            if submitted:
                user_id, username = check_login(email, password)

                if user_id:
                    # ログイン成功！セッションに情報を保存
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.success("ログイン成功！")
                    st.rerun()
                else:
                    st.error("メールアドレスかパスワードが間違っています")

    # 新規登録
    with tab2:
        st.write("新しくアカウントを作成します。")
        with st.form("signup_form"):
            new_username = st.text_input("ユーザー名（表示名）")
            new_email = st.text_input("メールアドレス")
            new_password = st.text_input("パスワード", type="password")

            submitted_signup = st.form_submit_button("登録する", type="primary")

            if submitted_signup:
                if not new_username or not new_email or not new_password:
                    st.warning("すべての項目を入力してください")
                else:
                    # 登録関数を呼ぶ
                    success, msg = register_user(new_username, new_email, new_password)
                    if success:
                        st.success(msg)
                        st.info("「ログイン」タブからログインしてください。")
                    else:
                        st.error(msg)

    # リセット申請
    with tab3:
        st.write("登録したメールアドレスを入力してください。")
        st.info("開発モードのため、リセット用URLはターミナルに表示されます。")

        with st.form("reset_request_form"):
            reset_email = st.text_input("メールアドレス")
            submitted_reset = st.form_submit_button("リセットリンクを発行")

            if submitted_reset:
                if issue_reset_token(reset_email):
                    st.success("リセット用URLを発行しました！")
                    st.warning("ターミナルを確認してください！")
                else:
                    st.error("そのメールアドレスは見つかりません。")

    # ここで処理を止める
    st.stop()


# ログインしている場合
st.sidebar.success(f"ログイン中:{st.session_state.username}")

# ログアウトボタン
if st.sidebar.button("ログアウト"):
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.rerun()


st.title("せどリスト")

# サイドバーにメニューを作る
with st.sidebar:
    st.header("メニュー")

    menu = st.pills(
        "",
        ["在庫一覧", "仕入れ登録", "設定"],
        selection_mode="single",
        default="在庫一覧",
    )

# ---A.在庫一覧画面---
if menu == "在庫一覧" or menu is None:
    st.subheader("現在の在庫一覧")

    # データを取得
    df_items = load_items(st.session_state.user_id)

    # 表示モード切替スイッチ
    view_mode = st.radio(
        "表示モード", ["表形式（PC向け）", "カード形式（スマホ向け）"], horizontal=True
    )

    if view_mode == "表形式（PC向け）":

        display_df = df_items[
            ["id", "name", "price", "shop", "quantity", "memo", "created_at"]
        ]
        display_df.columns = [
            "ID",
            "商品名",
            "価格",
            "店舗",
            "在庫数",
            "メモ",
            "登録日",
        ]

        edited_df = st.data_editor(
            display_df,
            key="editor",
            # num_rows="dynamic",
            column_config={
                "ID": st.column_config.NumberColumn(disabled=True),
                "登録日": st.column_config.DatetimeColumn(
                    disabled=True, format="YYYY-MM-DD HH:mm"
                ),
            },
            use_container_width=True,
            hide_index=True,
        )

        needs_rerun = False

        # 更新処理
        if st.session_state.editor:
            changes = st.session_state.editor

            # 編集されたデータ（edited_rows）
            if changes["edited_rows"]:
                for index, updates in changes["edited_rows"].items():
                    # 変更された行のIDを取得
                    item_id = df_items.iloc[index]["id"]

                    col_map = {
                        "商品名": "name",
                        "価格": "price",
                        "店舗": "shop",
                        "在庫数": "quantity",
                        "メモ": "memo",
                    }

                    for col_name, new_value in updates.items():
                        db_col = col_map.get(col_name)

                        if db_col:
                            update_item(item_id, db_col, new_value)
                            st.toast(f"ID:{item_id}の{col_name}を更新しました！")

                needs_rerun = True

            # 削除されたデータ（deleted_rows）
            if changes["deleted_rows"]:
                for index in changes["deleted_rows"]:
                    item_id = df_items.iloc[index]["id"]
                    delete_item(item_id)
                    st.toast(f"ID:{item_id}を削除しました")

                needs_rerun = True

            if needs_rerun:
                import time

                time.sleep(0.5)
                st.rerun()

    else:
        # スマホ向け：カード形式
        st.write("スマホ編集モード。タップして詳細を開く")

        # データを1行ずつ取り出してループする
        # iterrows()はデータフレームを1行ずつ処理する命令
        for index, row in df_items.iterrows():
            item_id = row["id"]
            item_name = row["name"]

            # Expanderを作る
            with st.expander(f"{item_name}(残:{row['quantity']}個)"):

                # 編集フォーム
                # keyにitem_idをつけることで、どの商品の入力欄か区別する
                new_name = st.text_input(
                    "商品名", value=row["name"], key=f"name_{item_id}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    new_price = st.number_input(
                        "価格", value=row["price"], step=100, key=f"price_{item_id}"
                    )
                with col2:
                    new_quantity = st.number_input(
                        "在庫数", value=row["quantity"], step=1, key=f"qty_{item_id}"
                    )

                new_shop = st.text_input(
                    "店舗", value=row["shop"], key=f"shop_{item_id}"
                )
                new_memo = st.text_area(
                    "メモ", value=row["memo"], key=f"memo_{item_id}"
                )

                # ボタンエリア
                btn_col1, btn_col2 = st.columns(2)

                with btn_col1:
                    if st.button(
                        "更新", key=f"update_{item_id}", use_container_width=True
                    ):
                        # UPDATE関数を呼ぶ
                        update_item(item_id, "name", new_name)
                        update_item(item_id, "price", new_price)
                        update_item(item_id, "quantity", new_quantity)
                        update_item(item_id, "shop", new_shop)
                        update_item(item_id, "memo", new_memo)
                        st.toast(f"{new_name}を更新しました！")
                        st.rerun()

                with btn_col2:
                    if st.button(
                        "削除",
                        key=f"del_{item_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        delete_item(item_id)
                        st.toast("削除しました")
                        st.rerun()


# ---B.在庫管理画面---
elif menu == "仕入れ登録":

    # セッションステートの初期化
    if "input_name" not in st.session_state:
        st.session_state.input_name = ""
    if "input_price" not in st.session_state:
        st.session_state.input_price = 0
    if "input_quantity" not in st.session_state:
        st.session_state.input_quantity = 1
    if "input_shop" not in st.session_state:
        st.session_state.input_shop = ""
    if "input_memo" not in st.session_state:
        st.session_state.input_memo = ""

    # ヘッダーとカメラ起動ボタンを横並びにする
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("新規登録")

    with col2:
        # カメラON・OFFのスイッチ
        use_camera = st.toggle("カメラ起動")

    # カメラを起動する
    if use_camera:
        picture = st.camera_input("値札を撮影")

        # 撮った写真を表示
        if picture:
            result = analyze_image_with_gemini(picture)
            if result:
                st.success("読み取り成功")
                st.session_state.input_name = result.get("name", "")
                st.session_state.input_price = result.get("price", 0)

                # デバック表示
                # st.json(result)

    # 入力フォームの作成
    with st.form("register_form"):
        # 入力欄を並べる
        name = st.text_input("商品名", key="input_name")

        col1, col2 = st.columns(2)
        with col1:
            price = st.number_input(
                "仕入れ価格", min_value=0, step=100, key="input_price"
            )
        with col2:
            quantity = st.number_input("個数", min_value=1, key="input_quantity")

        shop = st.text_input("仕入先（店舗名）", key="input_shop")
        memo = st.text_area("メモ", key="input_memo")

        # ボタンエリア
        btn_col1, btn_col2 = st.columns([1, 1])

        with btn_col1:
            submitted = st.form_submit_button(
                "登録する", type="primary", use_container_width=True
            )

        with btn_col2:
            clear_btn = st.form_submit_button(
                "入力をクリア", on_click=clear_form_state, use_container_width=True
            )

        # 登録ボタンが押された場合
        if submitted:
            if name:
                register_item(
                    st.session_state.user_id, name, price, shop, quantity, memo
                )
            else:
                st.warning("商品名は必須です！")


# C.設定画面
elif menu == "設定":
    st.subheader("アカウント設定")

    # ユーザー名変更エリア
    with st.expander("ユーザー名変更", expanded=False):
        with st.form("change_username_form"):
            # 現在のユーザー名
            st.text_input(
                "現在のユーザー名", value=st.session_state.username, disabled=True
            )

            # 新しいユーザー名
            new_name = st.text_input("新しいユーザー名")

            submitted_name = st.form_submit_button("変更する", type="primary")

            if submitted_name:
                if not new_name:
                    st.warning("名前を入力してください")
                elif new_name == st.session_state.username:
                    st.info("現在と同じ名前です")
                else:
                    # DBを更新
                    if update_username(st.session_state.user_id, new_name):
                        st.session_state.username = new_name
                        st.success(f"ユーザー名を「{new_name}」に変更しました！")

                        # 表示を即座に更新するためのリロード
                        import time

                        time.sleep(1)
                        st.rerun()

    st.divider()  # 仕切り線

    # メールアドレス変更エリア
    with st.expander("メールアドレス変更", expanded=False):
        # まずは現在のメアドを取得
        current_email = get_user_email(st.session_state.user_id)

        with st.form("change_email_form"):
            # 現在のメアド（表示のみ）
            st.text_input("現在のメールアドレス", value=current_email, disabled=True)

            # 新しいメアド
            new_email = st.text_input("新しいメールアドレス")

            submitted_email = st.form_submit_button("変更する", type="primary")

            if submitted_email:
                if not new_email:
                    st.warning("新しいメールアドレスを入力してください")
                elif new_email == current_email:
                    st.info("現在と同じメールアドレスです")
                else:
                    # DBを更新
                    success, msg = update_email(st.session_state.user_id, new_email)

                    if success:
                        st.success(msg)
                        import time

                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)

    st.divider()  # 仕切り線

    # パスワード変更エリア
    with st.expander("パスワード変更", expanded=False):
        with st.form("change_password_form"):
            current_pw = st.text_input("現在のパスワード", type="password")
            new_pw = st.text_input("新しいパスワード", type="password")
            confirm_pw = st.text_input("新しいパスワード（確認）", type="password")

            btn_submit = st.form_submit_button("変更する", type="primary")

            if btn_submit:
                # バリデーション（入力チェック）
                if not current_pw or not new_pw:
                    st.error("パスワードを入力してください")
                elif new_pw != confirm_pw:
                    st.error("新しいパスワードが一致しません")
                else:
                    # 変更処理を実行
                    success, msg = change_password(
                        st.session_state.user_id, current_pw, new_pw
                    )

                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

    st.divider()  # 仕切り線

    # データ管理エリア
    with st.expander("CSV出力", expanded=False):
        st.write("現在の在庫データをCSV形式でダウンロードします。")

        # データを取得
        df_export = load_items(st.session_state.user_id)

        if not df_export.empty:
            # CSVに変換
            csv_data = df_export.to_csv(index=False).encode("utf-8-sig")

            # 現在時刻をファイル名に入れる
            from datetime import datetime

            now_str = datetime.now().strftime("%Y%m%d_%H%M")
            file_name = f"stock_data_{now_str}.csv"

            # ダウンロードボタン
            st.download_button(
                label="CSVをダウンロード",
                data=csv_data,
                file_name=file_name,
                mime="text/csv",
                type="primary",
            )
        else:
            st.info("ダウンロードするデータがありません。")

    st.divider()  # 仕切り線

    # 退会するエリア
    with st.expander("退会（アカウント削除）", expanded=False):

        st.info("退会すると、登録した在庫データは全て完全に削除され、復元できません。")

        # 誤操作防止のチェックボックス
        confirm_delete = st.checkbox("上記の注意事項を理解し、退会します")

        if confirm_delete:
            if st.button(
                "退会する(データを全消去)", type="primary", use_container_width=True
            ):
                # 削除実行
                if delete_user_account(st.session_state.user_id):
                    st.success("退会処理が完了しました。ご利用ありがとうございました。")

                    # セッションをクリアしてログアウト状態にする
                    st.session_state.logged_in = False
                    st.session_state.user_id = None
                    st.session_state.username = ""

                    # 少し待ってからリロード
                    import time

                    time.sleep(2)
                    st.rerun()
