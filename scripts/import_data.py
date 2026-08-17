from pathlib import Path
import sqlite3

import pandas as pd


project_folder = Path(__file__).resolve().parent.parent
csv_path = (
    project_folder
    / "data"
    / "EMU_QA_Master_Privacy_Cleaned_744.csv"
)
database_path = project_folder / "database" / "emu_chatbot.db"

df = pd.read_csv(csv_path, encoding="utf-8-sig")

required_columns = {
    "id",
    "question",
    "answer",
    "category_tr",
    "category_en",
    "language",
}

missing_columns = required_columns.difference(df.columns)

if missing_columns:
    raise ValueError(
        "Missing privacy-clean dataset columns: "
        + ", ".join(sorted(missing_columns))
    )

if len(df) != 744:
    raise ValueError(
        f"Expected 744 privacy-clean records, found {len(df)}."
    )

if df[list(required_columns)].isna().any().any():
    raise ValueError(
        "Privacy-clean dataset contains missing required values."
    )

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
        df[["category_tr", "category_en"]]
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
            row["category_tr"],
            row["category_en"],
        )

        category_id = category_ids[category_key]
        language_id = language_ids[row["language"]]

        knowledge_entries.append(
            (
                int(row["id"]),
                row["question"],
                row["answer"],
                category_id,
                language_id,
            )
        )

    cursor.execute("PRAGMA secure_delete = ON")
    cursor.execute("DELETE FROM knowledge_entries")

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

with sqlite3.connect(database_path) as vacuum_connection:
    vacuum_connection.execute("VACUUM")

print("Data imported successfully.")
print("Languages:", language_count)
print("Categories:", category_count)
print("Knowledge entries:", entry_count)
