from sqlalchemy import create_engine, text

DB_URL = "postgresql://ollaa_user:REMOVED_OLD_PASSWORD@localhost:5432/ollaa"

engine = create_engine(DB_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("Database connected successfully:", result.scalar())
