from __future__ import annotations

from pathlib import Path
import sqlite3


project_folder = Path(__file__).resolve().parent.parent
database_path = project_folder / "database" / "emu_chatbot.db"

required_columns = {
    "categories": {
        "description",
        "responsible_unit",
        "is_active",
    },
    "questions": {
        "subcategory_id",
        "answered_at",
    },
    "attachments": {
        "file_size",
    },
    "ai_suggestions": {
        "provider",
        "prompt_context",
        "was_used",
        "generated_at",
    },
}

required_tables = {
    "subcategories",
    "question_assignments",
    "audit_logs",
}

errors: list[str] = []

with sqlite3.connect(database_path) as connection:
    connection.execute("PRAGMA foreign_keys = ON")

    integrity_check = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    if integrity_check != "ok":
        errors.append(
            f"Integrity check failed: {integrity_check}"
        )

    foreign_key_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if foreign_key_errors:
        errors.append(
            f"Foreign key errors: {foreign_key_errors}"
        )

    schema_version = int(
        connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]
    )

    if schema_version != 2:
        errors.append(
            f"Expected schema version 2, found {schema_version}."
        )

    table_names = {
        str(row[0])
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        )
    }

    missing_tables = sorted(
        required_tables - table_names
    )

    if missing_tables:
        errors.append(
            "Missing tables: "
            + ", ".join(missing_tables)
        )

    for table_name, expected_columns in required_columns.items():
        actual_columns = {
            str(row[1])
            for row in connection.execute(
                f"PRAGMA table_info({table_name})"
            )
        }
        missing_columns = sorted(
            expected_columns - actual_columns
        )

        if missing_columns:
            errors.append(
                f"Missing {table_name} columns: "
                + ", ".join(missing_columns)
            )

    knowledge_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM knowledge_entries"
        ).fetchone()[0]
    )

    if knowledge_count != 744:
        errors.append(
            f"Expected 744 knowledge entries, found {knowledge_count}."
        )

    language_counts = {
        str(code): int(count)
        for code, count in connection.execute(
            """
            SELECT languages.code, COUNT(*)
            FROM knowledge_entries
            JOIN languages
                ON knowledge_entries.language_id = languages.id
            GROUP BY languages.code
            """
        )
    }

    expected_language_counts = {
        "tr": 603,
        "en": 141,
    }

    if language_counts != expected_language_counts:
        errors.append(
            "Unexpected language distribution: "
            f"{language_counts}"
        )

    unanswered_with_answered_at = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM questions
            WHERE status NOT IN ('answered', 'closed')
              AND answered_at IS NOT NULL
            """
        ).fetchone()[0]
    )

    if unanswered_with_answered_at:
        errors.append(
            "Unanswered questions have answered_at values."
        )

    active_assignment_duplicates = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT question_id
                FROM question_assignments
                WHERE is_active = 1
                GROUP BY question_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
    )

    if active_assignment_duplicates:
        errors.append(
            "A question has more than one active assignment."
        )

print("=== DATABASE VALIDATION ===")
print("Schema version:", schema_version)
print("Integrity check:", integrity_check)
print("Foreign key errors:", len(foreign_key_errors))
print("Knowledge entries:", knowledge_count)
print("Language distribution:", language_counts)
print("Required tables present:", not missing_tables)

if errors:
    print("\nValidation failed:")
    for error in errors:
        print("-", error)
    raise SystemExit(1)

print("\nDatabase validation passed.")
