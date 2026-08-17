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
        name_en TEXT NOT NULL UNIQUE,
        description TEXT,
        responsible_unit TEXT,
        is_active INTEGER NOT NULL DEFAULT 1
            CHECK (is_active IN (0, 1))
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS subcategories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        name_tr TEXT NOT NULL,
        name_en TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
            CHECK (is_active IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (category_id)
            REFERENCES categories(id),

        UNIQUE (category_id, name_tr),
        UNIQUE (category_id, name_en)
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
        subcategory_id INTEGER,
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
        answered_at TEXT,

        FOREIGN KEY (student_id)
            REFERENCES users(id),

        FOREIGN KEY (category_id)
            REFERENCES categories(id),

        FOREIGN KEY (subcategory_id)
            REFERENCES subcategories(id),

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
        file_size INTEGER NOT NULL DEFAULT 0
            CHECK (file_size >= 0),
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
        provider TEXT NOT NULL DEFAULT 'local',
        model_name TEXT NOT NULL,
        prompt_context TEXT,
        suggestion_text TEXT NOT NULL,
        accepted INTEGER NOT NULL DEFAULT 0,
        was_used INTEGER NOT NULL DEFAULT 0
            CHECK (was_used IN (0, 1)),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        generated_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (question_id)
            REFERENCES questions(id)
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS question_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        assigned_to_user_id INTEGER NOT NULL,
        assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER NOT NULL DEFAULT 1
            CHECK (is_active IN (0, 1)),

        FOREIGN KEY (question_id)
            REFERENCES questions(id),

        FOREIGN KEY (assigned_to_user_id)
            REFERENCES users(id)
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id INTEGER,
        timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE SET NULL
    )
    """
)

index_statements = (
    "CREATE INDEX IF NOT EXISTS idx_knowledge_entries_category "
    "ON knowledge_entries(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_knowledge_entries_language "
    "ON knowledge_entries(language_id)",
    "CREATE INDEX IF NOT EXISTS idx_subcategories_category_active "
    "ON subcategories(category_id, is_active)",
    "CREATE INDEX IF NOT EXISTS idx_questions_student_created "
    "ON questions(student_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_questions_status_created "
    "ON questions(status, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_questions_category "
    "ON questions(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_questions_subcategory "
    "ON questions(subcategory_id)",
    "CREATE INDEX IF NOT EXISTS idx_questions_assigned_staff "
    "ON questions(assigned_staff_id)",
    "CREATE INDEX IF NOT EXISTS idx_answers_question_created "
    "ON answers(question_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_attachments_question "
    "ON attachments(question_id)",
    "CREATE INDEX IF NOT EXISTS idx_ai_suggestions_question_generated "
    "ON ai_suggestions(question_id, generated_at)",
    "CREATE INDEX IF NOT EXISTS idx_question_assignments_question "
    "ON question_assignments(question_id, assigned_at)",
    "CREATE INDEX IF NOT EXISTS idx_question_assignments_user_active "
    "ON question_assignments(assigned_to_user_id, is_active)",
    "CREATE UNIQUE INDEX IF NOT EXISTS "
    "idx_question_assignments_one_active "
    "ON question_assignments(question_id) WHERE is_active = 1",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp "
    "ON audit_logs(user_id, timestamp DESC)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_timestamp "
    "ON audit_logs(entity_type, entity_id, timestamp DESC)",
)

for statement in index_statements:
    cursor.execute(statement)

cursor.execute(
    """
    CREATE TRIGGER IF NOT EXISTS
        validate_question_subcategory_insert
    BEFORE INSERT ON questions
    WHEN NEW.subcategory_id IS NOT NULL
     AND NOT EXISTS (
         SELECT 1
         FROM subcategories
         WHERE id = NEW.subcategory_id
           AND category_id = NEW.category_id
     )
    BEGIN
        SELECT RAISE(
            ABORT,
            'Subcategory does not belong to category'
        );
    END
    """
)

cursor.execute(
    """
    CREATE TRIGGER IF NOT EXISTS
        validate_question_subcategory_update
    BEFORE UPDATE OF category_id, subcategory_id
    ON questions
    WHEN NEW.subcategory_id IS NOT NULL
     AND NOT EXISTS (
         SELECT 1
         FROM subcategories
         WHERE id = NEW.subcategory_id
           AND category_id = NEW.category_id
     )
    BEGIN
        SELECT RAISE(
            ABORT,
            'Subcategory does not belong to category'
        );
    END
    """
)

cursor.execute("PRAGMA user_version = 2")

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
