from fastapi import HTTPException
import sqlite3

from src.consts import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS file_gpt_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            doc_id TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


def insert_mapping(filename: str, doc_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO file_gpt_map (filename, doc_id) VALUES (?, ?)",
            (filename, doc_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400, detail=f"File '{filename}' already exists in the database."
        )
    finally:
        conn.close()


# Fetch a mapping from the database
def get_mapping(filename: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT doc_id FROM file_gpt_map WHERE filename = ?", (filename,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        raise HTTPException(
            status_code=404, detail=f"No mapping found for file '{filename}'."
        )


def get_all_ingested():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM file_gpt_map")
    result = cursor.fetchall()
    conn.close()
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail=f"No files mapped")
