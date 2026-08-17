from pathlib import Path
import sqlite3


project_folder = Path(__file__).resolve().parent.parent
database_path = project_folder / "database" / "emu_chatbot.db"

connection = sqlite3.connect(database_path)
connection.execute("PRAGMA foreign_keys = ON")
cursor = connection.cursor()

corrections = [
    (
        "Burs İşleri (Bilgi)",
        "Scholarship Affairs (Information)",
        "Burs İşleri (Blgi)",
    ),
    (
        "Bilgi Yönetimi ve Hizmetleri Şubesi Öneri",
        "Information Management and Services Branch Suggestion",
        "Bilgi Yönetimi ve Hizmetleri Şubesi Öneri",
    ),
    (
        "Mezuniyet İşlemi Otomatik E-posta",
        "Graduation Procedures Automatic Email",
        "Mezuniyet İşlemi Otomatik E-posta",
    ),
    (
        "Mezuniyet İşlemleri (İlişki Kesme, Diploma Onay)",
        "Graduation Procedures (Disenrollment, Diploma Approval)",
        "Mezuniyet İşlemleri (İlişki Kesme, Diploma Onay)",
    ),
    (
        "Öğrenci İşleri Öneri",
        "Student Affairs Suggestion",
        "Öğrenci İşleri Öneri",
    ),
]

updated_count = 0

try:
    for new_name_tr, new_name_en, old_name_tr in corrections:
        cursor.execute(
            """
            UPDATE categories
            SET name_tr = ?, name_en = ?
            WHERE name_tr = ?
            """,
            (
                new_name_tr,
                new_name_en,
                old_name_tr,
            ),
        )

        updated_count += cursor.rowcount

    connection.commit()

except Exception:
    connection.rollback()
    raise

cursor.execute("SELECT COUNT(*) FROM categories")
category_count = cursor.fetchone()[0]

connection.close()

print("Categories updated:", updated_count)
print("Total categories:", category_count)