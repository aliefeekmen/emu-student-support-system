from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_database(
    database_path: Path,
) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def write_audit_log(
    connection: sqlite3.Connection,
    *,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
) -> None:
    connection.execute(
        """
        INSERT INTO audit_logs (
            user_id,
            action,
            entity_type,
            entity_id
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            action,
            entity_type,
            entity_id,
        ),
    )


def record_question_assignment(
    connection: sqlite3.Connection,
    *,
    question_id: int,
    assigned_to_user_id: int,
) -> None:
    connection.execute(
        """
        UPDATE question_assignments
        SET is_active = 0
        WHERE question_id = ?
          AND is_active = 1
        """,
        (question_id,),
    )

    connection.execute(
        """
        INSERT INTO question_assignments (
            question_id,
            assigned_to_user_id,
            is_active
        )
        VALUES (?, ?, 1)
        """,
        (
            question_id,
            assigned_to_user_id,
        ),
    )


def close_question_assignment(
    connection: sqlite3.Connection,
    *,
    question_id: int,
) -> None:
    connection.execute(
        """
        UPDATE question_assignments
        SET is_active = 0
        WHERE question_id = ?
          AND is_active = 1
        """,
        (question_id,),
    )
