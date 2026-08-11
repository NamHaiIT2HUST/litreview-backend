import sqlite3
import os

try:
    c = sqlite3.connect('data/app.db')
    
    # Update papers
    c.execute("UPDATE papers SET id = REPLACE(id, '-', '') WHERE id LIKE '%-%'")
    c.execute("UPDATE papers SET project_id = REPLACE(project_id, '-', '') WHERE project_id LIKE '%-%'")
    c.execute("UPDATE papers SET search_query_id = REPLACE(search_query_id, '-', '') WHERE search_query_id LIKE '%-%'")
    
    # Update search_queries
    c.execute("UPDATE search_queries SET id = REPLACE(id, '-', '') WHERE id LIKE '%-%'")
    c.execute("UPDATE search_queries SET project_id = REPLACE(project_id, '-', '') WHERE project_id LIKE '%-%'")
    c.execute("UPDATE search_queries SET is_duplicated_from = REPLACE(is_duplicated_from, '-', '') WHERE is_duplicated_from LIKE '%-%'")
    
    c.commit()
    print("Fixed UUID dashes in SQLite!")
except Exception as e:
    print(f"Error: {e}")
