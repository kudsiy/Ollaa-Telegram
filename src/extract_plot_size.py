import re
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://postgres:REMOVED_OLD_PASSWORD@localhost:5432/ollaa"

engine = create_engine(DB_URL)

PLOT_REGEX = re.compile(
    r'(plot|land)\s*(size)?\s*[:\-]?\s*(\d{2,4})\s*(sqm|m2)',
    re.IGNORECASE
)


with engine.begin() as conn:
    rows = conn.execute(
        text("SELECT id, text FROM telegram_listings WHERE plot_sqm IS NULL")
    ).fetchall()

    for row in rows:
        match = PLOT_REGEX.search(row.text)
        if match:
            plot_size = int(match.group(3))


            # sanity check (ignore nonsense)
            if 50 <= plot_size <= 5000:
                conn.execute(
                    text("""
                        UPDATE telegram_listings
                        SET plot_sqm = :plot
                        WHERE id = :id
                    """),
                    {"plot": plot_size, "id": row.id}
                )

print("Plot size extraction complete")
