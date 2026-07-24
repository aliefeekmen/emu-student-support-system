from pathlib import Path
import sqlite3
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException


project_folder = Path(__file__).resolve().parent.parent
database_path = project_folder / "database" / "dau_chatbot.db"

app = FastAPI(
    title="DAU Student Support API",
    description="Backend API for the DAU student support system.",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "DAU Student Support API is running."
    }


@app.get("/health")
def health_check():
    with sqlite3.connect(database_path) as connection:
        connection.execute("SELECT 1")

    return {
        "status": "healthy",
        "database": "connected",
    }


@app.get("/stats")
def database_statistics():
    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM knowledge_entries"
        )
        knowledge_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM categories"
        )
        category_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM languages"
        )
        language_count = cursor.fetchone()[0]

    return {
        "knowledge_entries": knowledge_count,
        "categories": category_count,
        "languages": language_count,
    }
@app.get("/categories")
def list_categories():
    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, name_tr, name_en
            FROM categories
            ORDER BY name_tr
            """
        )

        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "name_tr": row[1],
            "name_en": row[2],
        }
        for row in rows
    ]
@app.get("/knowledge")
def list_knowledge_entries(
    language: str | None = None,
    category_id: int | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)

    conditions = []
    parameters = []

    if language:
        conditions.append("languages.code = ?")
        parameters.append(language.lower())

    if category_id:
        conditions.append("categories.id = ?")
        parameters.append(category_id)

    if search:
        conditions.append(
            """
            (
                knowledge_entries.question LIKE ?
                OR knowledge_entries.answer LIKE ?
            )
            """
        )

        search_value = f"%{search}%"
        parameters.extend(
            [search_value, search_value]
        )

    where_clause = ""

    if conditions:
        where_clause = (
            "WHERE " + " AND ".join(conditions)
        )

    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM knowledge_entries
            JOIN categories
                ON knowledge_entries.category_id = categories.id
            JOIN languages
                ON knowledge_entries.language_id = languages.id
            {where_clause}
            """,
            parameters,
        )

        total = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT
                knowledge_entries.id,
                knowledge_entries.question,
                knowledge_entries.answer,
                categories.id,
                categories.name_tr,
                categories.name_en,
                languages.code
            FROM knowledge_entries
            JOIN categories
                ON knowledge_entries.category_id = categories.id
            JOIN languages
                ON knowledge_entries.language_id = languages.id
            {where_clause}
            ORDER BY knowledge_entries.id DESC
            LIMIT ? OFFSET ?
            """,
            parameters + [limit, offset],
        )

        rows = cursor.fetchall()

    items = [
        {
            "id": row[0],
            "question": row[1],
            "answer": row[2],
            "category": {
                "id": row[3],
                "name_tr": row[4],
                "name_en": row[5],
            },
            "language": row[6],
        }
        for row in rows
    ]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }
@app.get("/knowledge/{entry_id}")
def get_knowledge_entry(entry_id: int):
    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                knowledge_entries.id,
                knowledge_entries.question,
                knowledge_entries.answer,
                categories.id,
                categories.name_tr,
                categories.name_en,
                languages.code
            FROM knowledge_entries
            JOIN categories
                ON knowledge_entries.category_id = categories.id
            JOIN languages
                ON knowledge_entries.language_id = languages.id
            WHERE knowledge_entries.id = ?
            """,
            (entry_id,),
        )

        row = cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge entry not found.",
        )

    return {
        "id": row[0],
        "question": row[1],
        "answer": row[2],
        "category": {
            "id": row[3],
            "name_tr": row[4],
            "name_en": row[5],
        },
        "language": row[6],
    }
class QuestionCreate(BaseModel):
    student_id: int
    category_id: int
    language: str
    subject: str = Field(
        min_length=3,
        max_length=200,
    )
    question_text: str = Field(
        min_length=5,
    )


@app.post("/questions", status_code=201)
def create_question(question: QuestionCreate):
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT users.id, roles.name
            FROM users
            JOIN roles
                ON users.role_id = roles.id
            WHERE users.id = ?
              AND users.is_active = 1
            """,
            (question.student_id,),
        )

        student = cursor.fetchone()

        if student is None or student[1] != "student":
            raise HTTPException(
                status_code=400,
                detail="Valid student account required.",
            )

        cursor.execute(
            """
            SELECT id
            FROM categories
            WHERE id = ?
            """,
            (question.category_id,),
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid category.",
            )

        cursor.execute(
            """
            SELECT id
            FROM languages
            WHERE code = ?
            """,
            (question.language.lower(),),
        )

        language = cursor.fetchone()

        if language is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid language.",
            )

        cursor.execute(
            """
            INSERT INTO questions (
                student_id,
                category_id,
                language_id,
                subject,
                question_text
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                question.student_id,
                question.category_id,
                language[0],
                question.subject.strip(),
                question.question_text.strip(),
            ),
        )

        question_id = cursor.lastrowid
        connection.commit()

    return {
        "id": question_id,
        "status": "open",
        "message": "Question created successfully.",
    }

@app.get("/questions")
def list_questions(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)

    parameters = []
    where_clause = ""

    if status:
        where_clause = "WHERE questions.status = ?"
        parameters.append(status.lower())

    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            f"""
            SELECT
                questions.id,
                questions.subject,
                questions.question_text,
                questions.status,
                students.full_name,
                categories.name_tr,
                languages.code,
                staff.full_name,
                questions.created_at
            FROM questions
            JOIN users AS students
                ON questions.student_id = students.id
            JOIN categories
                ON questions.category_id = categories.id
            JOIN languages
                ON questions.language_id = languages.id
            LEFT JOIN users AS staff
                ON questions.assigned_staff_id = staff.id
            {where_clause}
            ORDER BY questions.id DESC
            LIMIT ? OFFSET ?
            """,
            parameters + [limit, offset],
        )

        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "subject": row[1],
            "question_text": row[2],
            "status": row[3],
            "student_name": row[4],
            "category": row[5],
            "language": row[6],
            "assigned_staff": row[7],
            "created_at": row[8],
        }
        for row in rows
    ]
class QuestionAssign(BaseModel):
    staff_id: int


@app.patch("/questions/{question_id}/assign")
def assign_question(
    question_id: int,
    assignment: QuestionAssign,
):
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT users.id
            FROM users
            JOIN roles
                ON users.role_id = roles.id
            WHERE users.id = ?
              AND roles.name = 'staff'
              AND users.is_active = 1
            """,
            (assignment.staff_id,),
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=400,
                detail="Valid staff account required.",
            )

        cursor.execute(
            """
            SELECT status
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        )

        question = cursor.fetchone()

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found.",
            )

        if question[0] in ("answered", "closed"):
            raise HTTPException(
                status_code=400,
                detail="Answered or closed question cannot be assigned.",
            )

        cursor.execute(
            """
            UPDATE questions
            SET
                assigned_staff_id = ?,
                status = 'assigned',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                assignment.staff_id,
                question_id,
            ),
        )

        connection.commit()

    return {
        "question_id": question_id,
        "staff_id": assignment.staff_id,
        "status": "assigned",
    }
class AnswerCreate(BaseModel):
    staff_id: int
    answer_text: str = Field(min_length=3)
    used_ai_suggestion: bool = False


@app.post(
    "/questions/{question_id}/answers",
    status_code=201,
)
def answer_question(
    question_id: int,
    answer: AnswerCreate,
):
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                status,
                assigned_staff_id
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        )

        question = cursor.fetchone()

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found.",
            )

        if question[0] in ("answered", "closed"):
            raise HTTPException(
                status_code=400,
                detail="Question has already been answered.",
            )

        if question[1] != answer.staff_id:
            raise HTTPException(
                status_code=403,
                detail="Question is not assigned to this staff member.",
            )

        cursor.execute(
            """
            SELECT users.id
            FROM users
            JOIN roles
                ON users.role_id = roles.id
            WHERE users.id = ?
              AND roles.name = 'staff'
              AND users.is_active = 1
            """,
            (answer.staff_id,),
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=400,
                detail="Valid staff account required.",
            )

        cursor.execute(
            """
            INSERT INTO answers (
                question_id,
                staff_id,
                answer_text,
                used_ai_suggestion
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                question_id,
                answer.staff_id,
                answer.answer_text.strip(),
                int(answer.used_ai_suggestion),
            ),
        )

        answer_id = cursor.lastrowid

        cursor.execute(
            """
            UPDATE questions
            SET
                status = 'answered',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (question_id,),
        )

        connection.commit()

    return {
        "answer_id": answer_id,
        "question_id": question_id,
        "status": "answered",
    }
@app.get("/questions/{question_id}")
def get_question_detail(question_id: int):
    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                questions.id,
                questions.subject,
                questions.question_text,
                questions.status,
                students.full_name,
                categories.name_tr,
                categories.name_en,
                languages.code,
                staff.full_name,
                questions.created_at,
                questions.updated_at
            FROM questions
            JOIN users AS students
                ON questions.student_id = students.id
            JOIN categories
                ON questions.category_id = categories.id
            JOIN languages
                ON questions.language_id = languages.id
            LEFT JOIN users AS staff
                ON questions.assigned_staff_id = staff.id
            WHERE questions.id = ?
            """,
            (question_id,),
        )

        question = cursor.fetchone()

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found.",
            )

        cursor.execute(
            """
            SELECT
                answers.id,
                answers.answer_text,
                users.full_name,
                answers.used_ai_suggestion,
                answers.created_at
            FROM answers
            JOIN users
                ON answers.staff_id = users.id
            WHERE answers.question_id = ?
            ORDER BY answers.id
            """,
            (question_id,),
        )

        answer_rows = cursor.fetchall()

    answers = [
        {
            "id": row[0],
            "answer_text": row[1],
            "staff_name": row[2],
            "used_ai_suggestion": bool(row[3]),
            "created_at": row[4],
        }
        for row in answer_rows
    ]

    return {
        "id": question[0],
        "subject": question[1],
        "question_text": question[2],
        "status": question[3],
        "student_name": question[4],
        "category": {
            "name_tr": question[5],
            "name_en": question[6],
        },
        "language": question[7],
        "assigned_staff": question[8],
        "created_at": question[9],
        "updated_at": question[10],
        "answers": answers,
    }