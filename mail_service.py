import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()


def send_reset_email(to_email, reset_url):
    """GmailのSMTPサーバーを使用して、パスワードリセットメールを送信する

    Args:
        to_email (str): 受信者のメールアドレス
        reset_url (str): パスワードリセット用のURL

    Returns:
        bool: メール送信の成否

    Notes:
        SendGridのSMTPサーバーを使用しようとしたが、
        ポリシー違反でできなかったため、GmailのSMTPサーバーを使用する
    """
    sender_email = os.getenv("MAIL_SENDER_ADDRESS")
    app_password = os.getenv("MAIL_APP_PASSWORD")

    if not sender_email or not app_password:
        print("環境変数が正しく設定されていません。メール送信できません。")
        return False

    # メールの設定
    subject = "【せどりすと】パスワードリセットのご案内"

    # HTMLメール本文
    html_content = f"""
    <html>
    <body>
        <p>いつも「せどりすと」をご利用いただきありがとうございます。</p>
        <p>パスワード再設定のリクエストを受け付けました。</p>
        <p>以下のリンクをクリックして、新しいパスワードを設定してください。</p>
        <p>
            <a href="{reset_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                パスワードを再設定する
            </a>
        </p>
        <p>リンクの有効期限は1時間です。</p>
        <p>もしこのメールに心当たりがない場合は、無視してください。</p>
        <hr>
        <p><small>※このメールは送信専用アドレスから送信されています。</small></p>
    </body>
    </html>
    """

    # メールオブジェクトの構築
    msg = MIMEMultipart()
    msg["From"] = f"せどりすと運営 <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    # SMTPサーバーの設定
    try:
        # GmailのSMTPサーバーを使用
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # TLS暗号化
        server.login(sender_email, app_password)  # 認証

        # メール送信
        server.send_message(msg)
        server.quit()
        print("メール送信に成功しました。")
        return True

    except Exception as e:
        print(f"メール送信に失敗しました: {e}")
        return False
