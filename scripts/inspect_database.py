from pathlib import Path
import sqlite3


project_folder = Path(__file__).resolve().parent.parent
database_path = project_folder / "database" / "dau_chatbot.db"

connection = sqlite3.connect(database_path)
cursor = connection.cursor()

cursor.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
    """
)

tables = cursor.fetchall()

print("=== DATABASE TABLES ===")

for table in tables:
    table_name = table[0]

    if table_name != "sqlite_sequence":
        print("\nTable:", table_name)

        cursor.execute(
            f"PRAGMA table_info({table_name})"
        )

        columns = cursor.fetchall()

        for column in columns:
            print(
                "Column:",
                column[1],
                "| Type:",
                column[2],
                "| Required:",
                bool(column[3]),
                "| Primary key:",
                bool(column[5]),
            )

connection.close()