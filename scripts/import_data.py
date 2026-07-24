from pathlib import Path
import sqlite3

import pandas as pd


project_folder = Path(__file__).resolve().parent.parent
csv_path = project_folder / "data" / "Dau_chatbot_Cleaned_dataset.csv"
database_path = project_folder / "database" / "dau_chatbot.db"

df = pd.read_csv(csv_path, encoding="utf-8-sig")

connection = sqlite3.connect(database_path)
connection.execute("PRAGMA foreign_keys = ON")
cursor = connection.cursor()

try:
    languages = [
        ("tr", "Turkish"),
        ("en", "English"),
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO languages (code, name)
        VALUES (?, ?)
        """,
        languages,
    )

    category_rows = (
        df[["Kategori (TR)", "Kategori (EN)"]]
        .drop_duplicates()
        .values
        .tolist()
    )

    cursor.executemany(
        """
        INSERT OR IGNORE INTO categories (name_tr, name_en)
        VALUES (?, ?)
        """,
        category_rows,
    )

    cursor.execute(
        """
        SELECT id, code
        FROM languages
        """
    )

    language_ids = {
        code: language_id
        for language_id, code in cursor.fetchall()
    }

    cursor.execute(
        """
        SELECT id, name_tr, name_en
        FROM categories
        """
    )

    category_ids = {
        (name_tr, name_en): category_id
        for category_id, name_tr, name_en
        in cursor.fetchall()
    }

    knowledge_entries = []

    for _, row in df.iterrows():
        category_key = (
            row["Kategori (TR)"],
            row["Kategori (EN)"],
        )

        category_id = category_ids[category_key]
        language_id = language_ids[row["Dil"]]

        knowledge_entries.append(
            (
                int(row["ID"]),
                row["Soru"],
                row["Cevap"],
                category_id,
                language_id,
            )
        )

    cursor.executemany(
        """
        INSERT INTO knowledge_entries (
            id,
            question,
            answer,
            category_id,
            language_id
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            question = excluded.question,
            answer = excluded.answer,
            category_id = excluded.category_id,
            language_id = excluded.language_id
        """,
        knowledge_entries,
    )

    connection.commit()

except Exception:
    connection.rollback()
    raise

cursor.execute("SELECT COUNT(*) FROM languages")
language_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM categories")
category_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM knowledge_entries")
entry_count = cursor.fetchone()[0]

connection.close()

print("Data imported successfully.")
print("Languages:", language_count)
print("Categories:", category_count)
print("Knowledge entries:", entry_count)