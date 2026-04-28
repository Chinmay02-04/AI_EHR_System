import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS patients")

cur.execute("""
CREATE TABLE patients(
    name TEXT PRIMARY KEY,
    report TEXT,
    summary TEXT
)
""")

conn.commit()
conn.close()

print("✅ Patients table reset successfully!")