from pathlib import Path
import sqlite3


project_folder = Path(__file__).resolve().parent.parent
database_path = project_folder / "database" / "dau_chatbot.db"

connection = sqlite3.connect(database_path)
connection.execute("PRAGMA foreign_keys = ON")
cursor = connection.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS languages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_tr TEXT NOT NULL UNIQUE,
        name_en TEXT NOT NULL UNIQUE
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS knowledge_entries (
        id INTEGER PRIMARY KEY,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        language_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (category_id)
            REFERENCES categories(id),

        FOREIGN KEY (language_id)
            REFERENCES languages(id)
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        university_id TEXT UNIQUE,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role_id INTEGER NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (role_id)
            REFERENCES roles(id)
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        language_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        question_text TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open'
            CHECK (
                status IN (
                    'open',
                    'assigned',
                    'answered',
                    'closed'
                )
            ),
        assigned_staff_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (student_id)
            REFERENCES users(id),

        FOREIGN KEY (category_id)
            REFERENCES categories(id),

        FOREIGN KEY (language_id)
            REFERENCES languages(id),

        FOREIGN KEY (assigned_staff_id)
            REFERENCES users(id)
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        staff_id INTEGER NOT NULL,
        answer_text TEXT NOT NULL,
        used_ai_suggestion INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (question_id)
            REFERENCES questions(id),

        FOREIGN KEY (staff_id)
            REFERENCES users(id)
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        mime_type TEXT,
        uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (question_id)
            REFERENCES questions(id)
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS ai_suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        model_name TEXT NOT NULL,
        suggestion_text TEXT NOT NULL,
        accepted INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (question_id)
            REFERENCES questions(id)
    )
    """
)

cursor.executemany(
    """
    INSERT OR IGNORE INTO roles (name)
    VALUES (?)
    """,
    [
        ("student",),
        ("staff",),
        ("admin",),
    ],
)

connection.commit()
connection.close()

print("Database created successfully.")
print("Database location:")
print(database_path)