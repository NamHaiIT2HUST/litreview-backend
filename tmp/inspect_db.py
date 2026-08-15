import sqlite3
import os

db_path = "data/app.db"
out_path = "tmp/inspect_out_actual.txt"

with open(out_path, "w", encoding="utf-8") as f:
    f.write(f"Inspect DB. Exists: {os.path.exists(db_path)}\n")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, project_id, title, source, pdf_status, active_ingestion_id, created_at FROM papers")
            rows = cursor.fetchall()
            f.write(f"Total papers: {len(rows)}\n")
            for r in rows:
                desc = [d[0] for d in cursor.description]
                f.write(str(dict(zip(desc, r))) + "\n")
        except Exception as e:
            f.write(f"Error querying papers: {e}\n")
        conn.close()
    else:
        f.write("DB file does not exist\n")
print("Done")
