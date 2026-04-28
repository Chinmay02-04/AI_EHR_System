import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

# Remove all duplicate rows, keep only one per user
cur.execute("""
DELETE FROM patients
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM patients
    GROUP BY name
)
""")

conn.commit()

print("✅ Duplicate records removed successfully!")

conn.close()