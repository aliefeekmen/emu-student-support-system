from pathlib import Path
import sqlite3

import bcrypt


project_folder = Path(__file__).resolve().parent.parent
database_path = project_folder / "database" / "emu_chatbot.db"

demo_users = [
    {
        "university_id": "25000001",
        "full_name": "Demo Student",
        "email": "student@demo.local",
        "password": "123",
        "role": "student",
    },
    {
        "university_id": "STAFF001",
        "full_name": "Demo Staff",
        "email": "staff@demo.local",
        "password": "123",
        "role": "staff",
    },
    {
        "university_id": "ADMIN001",
        "full_name": "Demo Admin",
        "email": "admin@demo.local",
        "password": "123",
        "role": "admin",
    },
]

connection = sqlite3.connect(database_path)
connection.execute("PRAGMA foreign_keys = ON")
cursor = connection.cursor()

cursor.execute(
    """
    SELECT id, name
    FROM roles
    """
)

role_ids = {
    role_name: role_id
    for role_id, role_name in cursor.fetchall()
}

try:
    for user in demo_users:
        password_hash = bcrypt.hashpw(
            user["password"].encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        cursor.execute(
            """
            INSERT INTO users (
                university_id,
                full_name,
                email,
                password_hash,
                role_id
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                university_id = excluded.university_id,
                full_name = excluded.full_name,
                password_hash = excluded.password_hash,
                role_id = excluded.role_id
            """,
            (
                user["university_id"],
                user["full_name"],
                user["email"],
                password_hash,
                role_ids[user["role"]],
            ),
        )

    connection.commit()

except Exception:
    connection.rollback()
    raise

cursor.execute(
    """
    SELECT
        users.id,
        users.full_name,
        users.email,
        roles.name
    FROM users
    JOIN roles
        ON users.role_id = roles.id
    ORDER BY users.id
    """
)

users = cursor.fetchall()
connection.close()

print("=== DEMO USERS ===")

for user_id, full_name, email, role in users:
    print(
        user_id,
        "|",
        full_name,
        "|",
        email,
        "|",
        role,
    )
