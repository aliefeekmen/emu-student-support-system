from __future__ import annotations

from pathlib import Path
import sqlite3


project_folder = Path(__file__).resolve().parent.parent
database_path = project_folder / "database" / "dau_chatbot.db"
output_path = project_folder / "database" / "dau_chatbot.sql"


with sqlite3.connect(database_path) as connection:
    schema_version = int(
        connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]
    )
    dump_lines = list(connection.iterdump())

header = [
    "-- EMU Student Support database export",
    f"-- Schema version: {schema_version}",
    "PRAGMA foreign_keys = OFF;",
]
footer = [
    f"PRAGMA user_version = {schema_version};",
    "PRAGMA foreign_keys = ON;",
    "",
]

output_path.write_text(
    "\n".join(header + dump_lines + footer),
    encoding="utf-8",
)

print("Database SQL export created:")
print(output_path)
print("Schema version:", schema_version)
