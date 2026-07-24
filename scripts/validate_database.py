from pathlib import Path
import sqlite3


project_folder = Path(__file__).resolve().parent.parent
database_path = project_folder / "database" / "dau_chatbot.db"

connection = sqlite3.connect(database_path)
connection.execute("PRAGMA foreign_keys = ON")
cursor = connection.cursor()

print("=== FOREIGN KEY CHECK ===")

cursor.execute("PRAGMA foreign_key_check")
foreign_key_errors = cursor.fetchall()

if foreign_key_errors:
    print("Foreign key errors:", foreign_key_errors)
else:
    print("No foreign key errors.")

print("\n=== LANGUAGE DISTRIBUTION ===")

cursor.execute(
    """
    SELECT
        languages.code,
        COUNT(knowledge_entries.id)
    FROM knowledge_entries
    JOIN languages
        ON knowledge_entries.language_id = languages.id
    GROUP BY languages.code
    ORDER BY languages.code
    """
)

for language, count in cursor.fetchall():
    print(language, ":", count)

print("\n=== SAMPLE NORMALIZED RECORD ===")

cursor.execute(
    """
    SELECT
        knowledge_entries.id,
        knowledge_entries.question,
        categories.name_tr,
        categories.name_en,
        languages.code
    FROM knowledge_entries
    JOIN categories
        ON knowledge_entries.category_id = categories.id
    JOIN languages
        ON knowledge_entries.language_id = languages.id
    ORDER BY knowledge_entries.id DESC
    LIMIT 1
    """
)

record = cursor.fetchone()

print("ID:", record[0])
print("Question:", record[1])
print("Category TR:", record[2])
print("Category EN:", record[3])
print("Language:", record[4])

connection.close()