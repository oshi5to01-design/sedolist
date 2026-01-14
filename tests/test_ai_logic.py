from unittest.mock import patch

import ai_logic


@patch("ai_logic.genai.GenerativeModel")
@patch("ai_logic.Image.open")
@patch("ai_logic.st")
def test_analyze_image_clean_json(mock_st, mock_open, mock_model_cls):
    """正常系: クリーンなJSONのみが返ってくる場合

    Args:
        mock_st (MagicMock): Streamlitのモック
        mock_open (MagicMock): PIL.Image.openのモック
        mock_model_cls (MagicMock): genai.GenerativeModelのモック

    Returns:
        None
    """
    mock_instance = mock_model_cls.return_value
    # AIの返答を設定
    mock_instance.generate_content.return_value.text = (
        '{"name": "Clean Item", "price": 100}'
    )

    result = ai_logic.analyze_image_with_gemini("dummy.jpg")

    assert result is not None
    assert result["name"] == "Clean Item"
    assert result["price"] == 100


@patch("ai_logic.genai.GenerativeModel")
@patch("ai_logic.Image.open")
@patch("ai_logic.st")
def test_analyze_image_markdown_json(mock_st, mock_open, mock_model_cls):
    """正常系: Markdown記法や余計な文章が含まれる場合

    Args:
        mock_st (MagicMock): Streamlitのモック
        mock_open (MagicMock): PIL.Image.openのモック
        mock_model_cls (MagicMock): genai.GenerativeModelのモック

    Returns:
        None
    """
    mock_instance = mock_model_cls.return_value
    mock_instance.generate_content.return_value.text = """
    Here is the result:
    ```json
    {
        "name": "Markdown Item",
        "price": 2000
    }
    ```
    I hope this helps!
    """

    result = ai_logic.analyze_image_with_gemini("dummy.jpg")

    assert result is not None
    assert result["name"] == "Markdown Item"
    assert result["price"] == 2000


@patch("ai_logic.genai.GenerativeModel")
@patch("ai_logic.Image.open")
@patch("ai_logic.st")
def test_analyze_image_no_json(mock_st, mock_open, mock_model_cls):
    """異常系: JSONが含まれていない場合

    Args:
        mock_st (MagicMock): Streamlitのモック
        mock_open (MagicMock): PIL.Image.openのモック
        mock_model_cls (MagicMock): genai.GenerativeModelのモック

    Returns:
        None
    """
    mock_instance = mock_model_cls.return_value
    mock_instance.generate_content.return_value.text = (
        "Sorry, I could not find any price tag."
    )

    result = ai_logic.analyze_image_with_gemini("dummy.jpg")

    assert result is None
    # エラーメッセージが表示されたか確認
    mock_st.error.assert_called_with("AIからの応答にJSONが含まれていませんでした。")


@patch("ai_logic.genai.GenerativeModel")
@patch("ai_logic.Image.open")
@patch("ai_logic.st")
def test_analyze_image_api_error(mock_st, mock_open, mock_model_cls):
    """異常系: API呼び出しで例外が発生した場合

    Args:
        mock_st (MagicMock): Streamlitのモック
        mock_open (MagicMock): PIL.Image.openのモック
        mock_model_cls (MagicMock): genai.GenerativeModelのモック

    Returns:
        None
    """
    mock_instance = mock_model_cls.return_value
    mock_instance.generate_content.side_effect = Exception("API Error")

    result = ai_logic.analyze_image_with_gemini("dummy.jpg")

    assert result is None
    # エラーメッセージが表示されたか確認
    args, _ = mock_st.error.call_args
    assert "AI解析エラー:API Error" in args[0]
