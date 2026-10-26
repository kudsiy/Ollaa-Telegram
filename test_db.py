import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from settings import DB_URL

engine = create_engine(DB_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("Database connected successfully:", result.scalar())
