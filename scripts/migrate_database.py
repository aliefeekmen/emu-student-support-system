from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2


def table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        )
    }


def add_column_if_missing(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> bool:
    if column_name in table_columns(connection, table_name):
        return False

    connection.execute(
        f"ALTER TABLE {table_name} "
        f"ADD COLUMN {column_name} {definition}"
    )
    return True


def create_backup(
    database_path: Path,
    backup_path: Path,
) -> None:
    if backup_path.exists():
        raise FileExistsError(
            f"Backup already exists: {backup_path}"
        )

    backup_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with sqlite3.connect(database_path) as source:
        with sqlite3.connect(backup_path) as backup:
            source.backup(backup)


def resolve_attachment_size(
    project_folder: Path,
    relative_path: str,
) -> int | None:
    project_root = project_folder.resolve()
    file_path = (project_root / relative_path).resolve()

    if (
        file_path != project_root
        and project_root not in file_path.parents
    ):
        return None

    if not file_path.is_file():
        return None

    return file_path.stat().st_size


def migrate_database(
    database_path: Path,
    project_folder: Path,
) -> dict[str, Any]:
    database_path = database_path.resolve()
    project_folder = project_folder.resolve()

    if not database_path.is_file():
        raise FileNotFoundError(database_path)

    connection = sqlite3.connect(database_path)
    added_columns: list[str] = []
    missing_attachment_files: list[int] = []

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")

        connection.execute(
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

        column_specs = (
            (
                "categories",
                "description",
                "TEXT",
            ),
            (
                "categories",
                "responsible_unit",
                "TEXT",
            ),
            (
                "categories",
                "is_active",
                "INTEGER NOT NULL DEFAULT 1 "
                "CHECK (is_active IN (0, 1))",
            ),
            (
                "questions",
                "subcategory_id",
                "INTEGER REFERENCES subcategories(id)",
            ),
            (
                "questions",
                "answered_at",
                "TEXT",
            ),
            (
                "attachments",
                "file_size",
                "INTEGER NOT NULL DEFAULT 0 "
                "CHECK (file_size >= 0)",
            ),
            (
                "ai_suggestions",
                "provider",
                "TEXT NOT NULL DEFAULT 'local'",
            ),
            (
                "ai_suggestions",
                "prompt_context",
                "TEXT",
            ),
            (
                "ai_suggestions",
                "was_used",
                "INTEGER NOT NULL DEFAULT 0 "
                "CHECK (was_used IN (0, 1))",
            ),
            (
                "ai_suggestions",
                "generated_at",
                "TEXT",
            ),
        )

        for table_name, column_name, definition in column_specs:
            if add_column_if_missing(
                connection,
                table_name,
                column_name,
                definition,
            ):
                added_columns.append(
                    f"{table_name}.{column_name}"
                )

        connection.execute(
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

        connection.execute(
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

        connection.execute(
            """
            UPDATE questions
            SET answered_at = (
                SELECT MAX(answers.created_at)
                FROM answers
                WHERE answers.question_id = questions.id
            )
            WHERE answered_at IS NULL
              AND status IN ('answered', 'closed')
              AND EXISTS (
                  SELECT 1
                  FROM answers
                  WHERE answers.question_id = questions.id
              )
            """
        )

        connection.execute(
            """
            INSERT INTO question_assignments (
                question_id,
                assigned_to_user_id,
                assigned_at,
                is_active
            )
            SELECT
                questions.id,
                questions.assigned_staff_id,
                COALESCE(
                    questions.updated_at,
                    questions.created_at,
                    CURRENT_TIMESTAMP
                ),
                CASE
                    WHEN questions.status = 'assigned' THEN 1
                    ELSE 0
                END
            FROM questions
            WHERE questions.assigned_staff_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM question_assignments
                  WHERE question_assignments.question_id = questions.id
              )
            """
        )

        connection.execute(
            """
            UPDATE ai_suggestions
            SET
                was_used = accepted,
                generated_at = COALESCE(
                    generated_at,
                    created_at,
                    CURRENT_TIMESTAMP
                )
            """
        )

        attachment_rows = connection.execute(
            """
            SELECT id, file_path
            FROM attachments
            WHERE file_size = 0
            """
        ).fetchall()

        for attachment_id, relative_path in attachment_rows:
            actual_size = resolve_attachment_size(
                project_folder,
                str(relative_path),
            )

            if actual_size is None:
                missing_attachment_files.append(
                    int(attachment_id)
                )
                continue

            connection.execute(
                """
                UPDATE attachments
                SET file_size = ?
                WHERE id = ?
                """,
                (
                    actual_size,
                    attachment_id,
                ),
            )

        index_statements = (
            "CREATE INDEX IF NOT EXISTS "
            "idx_knowledge_entries_category "
            "ON knowledge_entries(category_id)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_knowledge_entries_language "
            "ON knowledge_entries(language_id)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_subcategories_category_active "
            "ON subcategories(category_id, is_active)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_questions_student_created "
            "ON questions(student_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_questions_status_created "
            "ON questions(status, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_questions_category "
            "ON questions(category_id)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_questions_subcategory "
            "ON questions(subcategory_id)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_questions_assigned_staff "
            "ON questions(assigned_staff_id)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_answers_question_created "
            "ON answers(question_id, created_at)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_attachments_question "
            "ON attachments(question_id)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_ai_suggestions_question_generated "
            "ON ai_suggestions(question_id, generated_at)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_question_assignments_question "
            "ON question_assignments(question_id, assigned_at)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_question_assignments_user_active "
            "ON question_assignments(assigned_to_user_id, is_active)",
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "idx_question_assignments_one_active "
            "ON question_assignments(question_id) "
            "WHERE is_active = 1",
            "CREATE INDEX IF NOT EXISTS "
            "idx_audit_logs_user_timestamp "
            "ON audit_logs(user_id, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS "
            "idx_audit_logs_entity_timestamp "
            "ON audit_logs(entity_type, entity_id, timestamp DESC)",
        )

        for statement in index_statements:
            connection.execute(statement)

        connection.execute(
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

        connection.execute(
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

        connection.execute(
            f"PRAGMA user_version = {SCHEMA_VERSION}"
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    verification = sqlite3.connect(database_path)
    try:
        verification.execute("PRAGMA foreign_keys = ON")
        tables = {
            str(row[0])
            for row in verification.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }
        required_tables = {
            "subcategories",
            "question_assignments",
            "audit_logs",
        }
        missing_tables = sorted(required_tables - tables)
        integrity_check = verification.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
        foreign_key_violations = [
            list(row)
            for row in verification.execute(
                "PRAGMA foreign_key_check"
            )
        ]
        schema_version = int(
            verification.execute(
                "PRAGMA user_version"
            ).fetchone()[0]
        )
        summary = {
            "status": "passed",
            "schema_version": schema_version,
            "added_columns": added_columns,
            "missing_required_tables": missing_tables,
            "knowledge_entries": int(
                verification.execute(
                    "SELECT COUNT(*) FROM knowledge_entries"
                ).fetchone()[0]
            ),
            "questions": int(
                verification.execute(
                    "SELECT COUNT(*) FROM questions"
                ).fetchone()[0]
            ),
            "answers": int(
                verification.execute(
                    "SELECT COUNT(*) FROM answers"
                ).fetchone()[0]
            ),
            "assignment_history_rows": int(
                verification.execute(
                    "SELECT COUNT(*) FROM question_assignments"
                ).fetchone()[0]
            ),
            "answered_at_rows": int(
                verification.execute(
                    """
                    SELECT COUNT(*)
                    FROM questions
                    WHERE answered_at IS NOT NULL
                    """
                ).fetchone()[0]
            ),
            "attachment_sizes_recorded": int(
                verification.execute(
                    """
                    SELECT COUNT(*)
                    FROM attachments
                    WHERE file_size > 0
                    """
                ).fetchone()[0]
            ),
            "missing_attachment_files": missing_attachment_files,
            "integrity_check": integrity_check,
            "foreign_key_violations": foreign_key_violations,
        }
    finally:
        verification.close()

    if (
        summary["schema_version"] != SCHEMA_VERSION
        or summary["missing_required_tables"]
        or summary["integrity_check"] != "ok"
        or summary["foreign_key_violations"]
    ):
        summary["status"] = "failed"
        raise RuntimeError(
            json.dumps(
                summary,
                ensure_ascii=False,
                indent=2,
            )
        )

    return summary


def default_backup_path(database_path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    return database_path.with_name(
        f"{database_path.stem}_pre_schema_v2_"
        f"{timestamp}{database_path.suffix}"
    )


def parse_args() -> argparse.Namespace:
    project_folder = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description=(
            "Upgrade the existing DAU chatbot SQLite database "
            "to schema version 2."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=(
            project_folder
            / "database"
            / "dau_chatbot.db"
        ),
    )
    parser.add_argument(
        "--project-folder",
        type=Path,
        default=project_folder,
    )
    parser.add_argument(
        "--backup",
        type=Path,
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_path = args.database.resolve()

    backup_path: Path | None = None
    if not args.skip_backup:
        backup_path = (
            args.backup.resolve()
            if args.backup
            else default_backup_path(database_path)
        )
        create_backup(database_path, backup_path)

    summary = migrate_database(
        database_path=database_path,
        project_folder=args.project_folder,
    )
    summary["backup"] = (
        str(backup_path)
        if backup_path is not None
        else None
    )
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
