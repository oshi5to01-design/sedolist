import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# データベースURLの構築
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"


def fix_schema():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Dropping sessions table...")
        conn.execute(text("DROP TABLE IF EXISTS sessions CASCADE"))
        print("Creating sessions table (via next app run)...")
        # app.pyでBase.metadata.create_all()を呼び出すことでテーブルが再作成される
        conn.commit()
    print("Done.")


if __name__ == "__main__":
    fix_schema()
