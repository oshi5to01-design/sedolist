import time
from datetime import datetime

import streamlit as st

import ai_logic as ai
import auth
import database as db


# ----------------------------------------------
# UI用ヘルパー関数
# ----------------------------------------------
def clear_form_state():
    """入力フォームをクリアするコールバック関数"""
    st.session_state.input_name = ""
    st.session_state.input_price = 0
    st.session_state.input_quantity = 1
    st.session_state.input_shop = ""
    st.session_state.input_memo = ""


# -----------------------------------------------
# 高速化エリア(Fragment)
# -----------------------------------------------
@st.fragment
def show_inventory_screen():
    """在庫一覧画面(部分更新対応)"""
    st.subheader("現在の在庫一覧")

    # dbモジュールからデータ取得
    df_items = db.load_items(st.session_state.user_id)

    view_mode = st.radio(
        "表示モード", ["表形式（PC向け）", "カード形式（スマホ向け）"], horizontal=True
    )

    if view_mode == "表形式（PC向け）":
        # 表示用に整形
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
            column_config={
                "ID": st.column_config.NumberColumn(disabled=True),
                "登録日": st.column_config.DatetimeColumn(
                    disabled=True, format="YYYY-MM-DD HH:mm"
                ),
            },
            use_container_width=True,
            hide_index=True,
        )

        # 更新処理
        if st.session_state.editor:
            changes = st.session_state.editor
            needs_rerun = False

            if changes["edited_rows"]:
                for index, updates in changes["edited_rows"].items():
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
                            # dbモジュールで更新
                            db.update_item(item_id, db_col, new_value)
                            st.toast(f"ID:{item_id} の {col_name} を更新しました！")
                needs_rerun = True

            if changes["deleted_rows"]:
                for index in changes["deleted_rows"]:
                    item_id = df_items.iloc[index]["id"]
                    # dbモジュールで削除
                    db.delete_item(item_id)
                    st.toast(f"ID:{item_id} を削除しました")
                needs_rerun = True

            if needs_rerun:
                time.sleep(0.5)
                st.rerun()

    else:
        # スマホ向けカード表示
        st.write("スマホ編集モード。タップして詳細を開く")
        for index, row in df_items.iterrows():
            item_id = row["id"]
            with st.expander(f"{row['name']} (残:{row['quantity']}個)"):
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

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button(
                        "更新", key=f"upd_{item_id}", use_container_width=True
                    ):
                        # dbモジュールで更新
                        db.update_item(item_id, "name", new_name)
                        db.update_item(item_id, "price", new_price)
                        db.update_item(item_id, "quantity", new_quantity)
                        db.update_item(item_id, "shop", new_shop)
                        db.update_item(item_id, "memo", new_memo)
                        st.toast(f"{new_name}を更新しました！")
                        st.rerun()
                with btn_col2:
                    if st.button(
                        "削除",
                        key=f"del_{item_id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        # dbモジュールで削除
                        db.delete_item(item_id)
                        st.toast("削除しました")
                        st.rerun()


@st.fragment
def show_register_screen():
    """仕入れ登録画面(部分更新対応)"""
    # セッションステート初期化
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

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("新規登録")
    with col2:
        use_camera = st.toggle("カメラ起動")

    if use_camera:
        picture = st.camera_input("値札を撮影")
        if picture:
            # aiモジュールで解析
            result = ai.analyze_image_with_gemini(picture)
            if result:
                st.success("読み取り成功")
                st.session_state.input_name = result.get("name", "")
                st.session_state.input_price = result.get("price", 0)

    with st.form("register_form"):
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

        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            submitted = st.form_submit_button(
                "登録する", type="primary", use_container_width=True
            )
        with btn_col2:
            clear_btn = st.form_submit_button(
                "入力をクリア", on_click=clear_form_state, use_container_width=True
            )

        if submitted:
            if name:
                # dbモジュールで登録
                db.register_item(
                    st.session_state.user_id, name, price, shop, quantity, memo
                )
            else:
                st.warning("商品名は必須です！")


# ----------------------------------------------
# メイン処理開始
# ----------------------------------------------

# セッションステートの初期化
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = ""

# URLからトークンを取得 (?token=xxxxx)
query_params = st.query_params
reset_token = query_params.get("token", None)

# ==========================================
# パターンA：パスワード再設定モード
# ==========================================
if reset_token:
    st.title("パスワード再設定")

    # authモジュールを使ってトークン検証
    user = auth.verify_reset_token(reset_token)

    if user:
        st.success(f"本人確認が完了しました。\n対象アカウント: {user[1]}")
        with st.form("new_password_form"):
            new_pw = st.text_input("新しいパスワード", type="password")
            submitted = st.form_submit_button("変更する")

            if submitted:
                if not new_pw:
                    st.warning("パスワードを入力してください")
                else:
                    # authモジュールでパスワード更新
                    if auth.reset_password(user[0], new_pw):
                        st.success("パスワードを変更しました！")
                        st.info("ログイン画面に戻ります")
                        time.sleep(2)
                        st.query_params.clear()
                        st.rerun()
    else:
        st.error("このリンクは無効か、有効期限が切れています。")
        if st.button("ログイン画面へ戻る"):
            st.query_params.clear()
            st.rerun()

    st.stop()  # ここで止める

# ==========================================
# パターンB：ログイン画面 (未ログイン時)
# ==========================================
if not st.session_state.logged_in:
    st.title("ログイン")

    tab1, tab2, tab3 = st.tabs(["ログイン", "新規登録", "パスワードを忘れた場合"])

    # --- ログイン ---
    with tab1:
        with st.form("login_form"):
            email = st.text_input("メールアドレス")
            show_password = st.checkbox("パスワードを表示して入力する")
            if show_password:
                password = st.text_input("パスワード", key="pw_visible")
            else:
                password = st.text_input("パスワード", type="password", key="pw_hidden")

            submitted = st.form_submit_button("ログイン")

            if submitted:
                # authモジュールでログインチェック
                user_id, username = auth.check_login(email, password)
                if user_id:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.success("ログイン成功！")
                    st.rerun()
                else:
                    st.error("メールアドレスかパスワードが間違っています")

    # --- 新規登録 ---
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
                    # authモジュールで登録
                    success, msg = auth.register_user(
                        new_username, new_email, new_password
                    )
                    if success:
                        st.success(msg)
                        st.info("「ログイン」タブからログインしてください。")
                    else:
                        st.error(msg)

    # --- リセット申請 ---
    with tab3:
        st.write("登録したメールアドレスを入力してください。")
        st.info("開発モードのため、リセット用URLはターミナルに表示されます。")
        with st.form("reset_request_form"):
            reset_email = st.text_input("メールアドレス")
            submitted_reset = st.form_submit_button("リセットリンクを発行")

            if submitted_reset:
                # authモジュールでトークン発行
                if auth.issue_reset_token(reset_email):
                    st.success("リセット用URLを発行しました！")
                    st.warning("ターミナルを確認してください！")
                else:
                    st.error("そのメールアドレスは見つかりません。")

    st.stop()  # ここで止める

# ==========================================
# パターンC：メインアプリ画面 (ログイン済み)
# ==========================================
st.sidebar.success(f"ログイン中: {st.session_state.username}")

if st.sidebar.button("ログアウト"):
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.rerun()

st.title("stock_manager")

# サイドバーメニュー
with st.sidebar:
    st.header("メニュー")
    menu = st.pills(
        "",
        ["在庫一覧", "仕入れ登録", "設定"],
        selection_mode="single",
        default="在庫一覧",
    )

# --- 1. 在庫一覧画面 ---
if menu == "在庫一覧" or menu is None:
    # フラグメント化した関数を呼ぶ
    show_inventory_screen()

# --- 2. 仕入れ登録画面 ---
elif menu == "仕入れ登録":
    # フラグメント化した関数を呼ぶ
    show_register_screen()

# --- 3. 設定画面 ---
elif menu == "設定":
    st.subheader("アカウント設定")

    # ユーザー名変更
    with st.expander("ユーザー名変更", expanded=False):
        with st.form("change_username_form"):
            st.text_input(
                "現在のユーザー名", value=st.session_state.username, disabled=True
            )
            new_name = st.text_input("新しいユーザー名")
            if st.form_submit_button("変更する", type="primary"):
                if not new_name:
                    st.warning("名前を入力してください")
                elif new_name == st.session_state.username:
                    st.info("現在と同じ名前です")
                else:
                    # dbモジュールで更新
                    if db.update_username(st.session_state.user_id, new_name):
                        st.session_state.username = new_name
                        st.success(f"ユーザー名を「{new_name}」に変更しました！")
                        time.sleep(1)
                        st.rerun()

    st.divider()

    # メールアドレス変更
    with st.expander("メールアドレス変更", expanded=False):
        current_email = db.get_user_email(st.session_state.user_id)  # dbを使う
        with st.form("change_email_form"):
            st.text_input("現在のメールアドレス", value=current_email, disabled=True)
            new_email = st.text_input("新しいメールアドレス")
            if st.form_submit_button("変更する", type="primary"):
                if not new_email:
                    st.warning("新しいメールアドレスを入力してください")
                elif new_email == current_email:
                    st.info("現在と同じメールアドレスです")
                else:
                    # dbモジュールで更新
                    success, msg = db.update_email(st.session_state.user_id, new_email)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)

    st.divider()

    # パスワード変更
    with st.expander("パスワード変更", expanded=False):
        with st.form("change_password_form"):
            current_pw = st.text_input("現在のパスワード", type="password")
            new_pw = st.text_input("新しいパスワード", type="password")
            confirm_pw = st.text_input("新しいパスワード（確認）", type="password")
            if st.form_submit_button("変更する", type="primary"):
                if not current_pw or not new_pw:
                    st.error("パスワードを入力してください")
                elif new_pw != confirm_pw:
                    st.error("新しいパスワードが一致しません")
                else:
                    # authモジュールで変更
                    success, msg = auth.change_password(
                        st.session_state.user_id, current_pw, new_pw
                    )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

    st.divider()

    # CSV出力
    with st.expander("CSV出力", expanded=False):
        st.write("現在の在庫データをCSV形式でダウンロードします。")
        df_export = db.load_items(st.session_state.user_id)  # dbを使う
        if not df_export.empty:
            csv_data = df_export.to_csv(index=False).encode("utf-8-sig")
            now_str = datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button(
                label="CSVをダウンロード",
                data=csv_data,
                file_name=f"stock_data_{now_str}.csv",
                mime="text/csv",
                type="primary",
            )
        else:
            st.info("ダウンロードするデータがありません。")

    st.divider()

    # 退会
    with st.expander("退会（アカウント削除）", expanded=False):
        st.info("退会すると、登録した在庫データは全て完全に削除され、復元できません。")
        confirm_delete = st.checkbox("上記の注意事項を理解し、退会します")
        if confirm_delete:
            if st.button(
                "退会する(データを全消去)", type="primary", use_container_width=True
            ):
                # dbモジュールで削除
                if db.delete_user_account(st.session_state.user_id):
                    st.success("退会処理が完了しました。ご利用ありがとうございました。")
                    st.session_state.logged_in = False
                    st.session_state.user_id = None
                    st.session_state.username = ""
                    time.sleep(2)
                    st.rerun()
