from sqlalchemy import text
from database import engine

with engine.connect() as conn:

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS sprints (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            goal TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'PLANNING',
            created_at TIMESTAMP DEFAULT NOW()
        );
    """))

    conn.execute(text("""
        ALTER TABLE issues
        ADD COLUMN IF NOT EXISTS sprint_id INTEGER REFERENCES sprints(id);
    """))

    conn.commit()

print("Done. sprint_id column has been added.")