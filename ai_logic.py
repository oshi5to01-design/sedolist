import json
import os
from typing import Any

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

# .env読み込み
load_dotenv()

# Geminiの設定
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def analyze_image_with_gemini(uploaded_file: Any) -> dict[str, Any] | None:
    """
    アップロードされた画像をGeminiに渡し、商品名と価格を抽出する。

    Args:
        uploaded_file: Streamlitのfile_uploaderやcamera_inputから渡される画像データ

    Returns:
        dict: {"name":"商品名","price":1000}のような辞書データ。
            失敗した場合は None を返す。
    """
    try:
        # 画像を読み込む
        image = Image.open(uploaded_file)

        # モデル
        model = genai.GenerativeModel("models/gemini-flash-latest")

        # プロンプト
        prompt = """
        この画像を分析して、以下の情報を抽出してください。
        
        1.商品名(name):パッケージや値札から読み取れる具体的な商品名
        2.価格(price):値札に書かれている価格(数字のみ、円マークやカンマは除く)

        出力は必ず以下のJSON形式のみにしてください。余計な文章は不要です。
        {
            "name":"商品名",
            "price":1000
        }
        """

        # AIに聞く
        with st.spinner("AIが画像を解析中"):
            response = model.generate_content([prompt, image])  # type: ignore
            text = response.text

            # JSON形式の文字列を探して取り出す
            # (Geminiが```json...```で囲ってくることがあるための除去)
            clean_text = text.replace("```json", "").replace("```", "").strip()

            # 辞書データに変換
            result = json.loads(clean_text)
            return result

    except Exception as e:
        st.error(f"AI解析エラー:{e}")
        return None
