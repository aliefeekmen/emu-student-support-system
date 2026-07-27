from pathlib import Path
import os
import bcrypt
import sqlite3
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


project_folder = Path(__file__).resolve().parent.parent
load_dotenv(project_folder / ".env")

session_secret = os.getenv("SESSION_SECRET")

if not session_secret:
    raise RuntimeError(
        "SESSION_SECRET environment variable is required."
    )
database_path = project_folder / "database" / "dau_chatbot.db"

app = FastAPI(
    title="DAU Student Support API",
    description="Backend API for the DAU student support system.",
    version="1.0.0",
)
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    same_site="lax",
    https_only=False,
    max_age=3600,
)
templates = Jinja2Templates(
    directory=str(project_folder / "templates")
)

app.mount(
    "/static",
    StaticFiles(
        directory=str(project_folder / "static")
    ),
    name="static",
)
def require_session_user(
    request: Request,
    allowed_roles: tuple[str, ...] | None = None,
) -> dict:
    user = request.session.get("user")

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    if (
        allowed_roles is not None
        and user["role"] not in allowed_roles
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission for this action.",
        )

    return user
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
def database_statistics(request: Request):
    require_session_user(
        request,
        allowed_roles=("staff", "admin"),
    )
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
def list_categories(request: Request):
    require_session_user(
        request,
        allowed_roles=("student", "staff", "admin"),
    )
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
    request: Request,
    language: str | None = None,
    category_id: int | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    require_session_user(
        request,
        allowed_roles=("student", "staff", "admin"),
    )

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
def get_knowledge_entry(
    request: Request,
    entry_id: int,
):
    require_session_user(
        request,
        allowed_roles=("student", "staff", "admin"),
    )
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
def create_question(
    request: Request,
    question: QuestionCreate,
):
    user = require_session_user(
        request,
        allowed_roles=("student",),
    )

    if question.student_id != user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You can only submit questions for your own account.",
        )
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
    request: Request,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    require_session_user(
        request,
        allowed_roles=("staff", "admin"),
    )

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
    request: Request,
    question_id: int,
    assignment: QuestionAssign,
):
    user = require_session_user(
        request,
        allowed_roles=("staff", "admin"),
    )

    if (
        user["role"] == "staff"
        and assignment.staff_id != user["id"]
    ):
        raise HTTPException(
            status_code=403,
            detail="Staff can only assign questions to themselves.",
        )
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
    request: Request,
    question_id: int,
    answer: AnswerCreate,
):
    user = require_session_user(
        request,
        allowed_roles=("staff", "admin"),
    )

    if (
        user["role"] == "staff"
        and answer.staff_id != user["id"]
    ):
        raise HTTPException(
            status_code=403,
            detail="Staff can only submit answers as themselves.",
        )
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
def get_question_detail(
    request: Request,
    question_id: int,
):
    user = require_session_user(
        request,
        allowed_roles=("student", "staff", "admin"),
    )

    if user["role"] == "student":
        with sqlite3.connect(database_path) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT 1
                FROM questions
                WHERE id = ?
                  AND student_id = ?
                """,
                (
                    question_id,
                    user["id"],
                ),
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=403,
                    detail="You can only view your own questions.",
                )
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
                students.university_id,
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
        "student_number": question[5],
        "category": {
            "name_tr": question[6],
            "name_en": question[7],
        },
        "language": question[8],
        "assigned_staff": question[9],
        "created_at": question[10],
        "updated_at": question[11],
        "answers": answers,
    }
@app.get("/dashboard", include_in_schema=False)
def dashboard_page(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    if user["role"] not in ("staff", "admin"):
        return RedirectResponse(
            url=dashboard_for_role(user["role"]),
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
        },
    )
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={},
    )
@app.get("/students/{student_id}/questions")
def list_student_questions(
    request: Request,
    student_id: int,
):
    user = require_session_user(
        request,
        allowed_roles=("student", "staff", "admin"),
    )

    if (
        user["role"] == "student"
        and student_id != user["id"]
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only view your own questions.",
        )
    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT users.id
            FROM users
            JOIN roles
                ON users.role_id = roles.id
            WHERE users.id = ?
              AND roles.name = 'student'
              AND users.is_active = 1
            """,
            (student_id,),
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found.",
            )

        cursor.execute(
            """
            SELECT
                questions.id,
                questions.subject,
                questions.question_text,
                questions.status,
                categories.id,
                categories.name_tr,
                categories.name_en,
                languages.code,
                questions.created_at,
                questions.updated_at,
                staff.full_name,

                (
                    SELECT answers.answer_text
                    FROM answers
                    WHERE answers.question_id = questions.id
                    ORDER BY answers.id DESC
                    LIMIT 1
                ) AS latest_answer,

                (
                    SELECT answers.created_at
                    FROM answers
                    WHERE answers.question_id = questions.id
                    ORDER BY answers.id DESC
                    LIMIT 1
                ) AS answer_date

            FROM questions

            JOIN categories
                ON questions.category_id = categories.id

            JOIN languages
                ON questions.language_id = languages.id

            LEFT JOIN users AS staff
                ON questions.assigned_staff_id = staff.id

            WHERE questions.student_id = ?

            ORDER BY questions.id DESC
            """,
            (student_id,),
        )

        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "subject": row[1],
            "question_text": row[2],
            "status": row[3],
            "category": {
                "id": row[4],
                "name_tr": row[5],
                "name_en": row[6],
            },
            "language": row[7],
            "created_at": row[8],
            "updated_at": row[9],
            "staff_name": row[10],
            "latest_answer": row[11],
            "answer_date": row[12],
        }
        for row in rows
    ]
@app.get(
    "/student-dashboard",
    include_in_schema=False,
)
@app.get(
    "/student-dashboard",
    include_in_schema=False,
)
def student_dashboard_page(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    if user["role"] != "student":
        return RedirectResponse(
            url=dashboard_for_role(user["role"]),
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="student_dashboard.html",
        context={
            "user": user,
        },
    )
    return templates.TemplateResponse(
        request=request,
        name="student_dashboard.html",
        context={},
    )
def dashboard_for_role(role_name: str) -> str:
    destinations = {
    "student": "/student-dashboard",
    "staff": "/dashboard",
    "admin": "/admin-dashboard",
}

    return destinations.get(role_name, "/login")


@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    user = request.session.get("user")

    if user:
        return RedirectResponse(
            url=dashboard_for_role(user["role"]),
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": None,
        },
    )


@app.post("/login", include_in_schema=False)
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                users.id,
                users.full_name,
                users.email,
                users.university_id,
                users.password_hash,
                roles.name
            FROM users
            JOIN roles
                ON users.role_id = roles.id
            WHERE lower(users.email) = lower(?)
              AND users.is_active = 1
            """,
            (email.strip(),),
        )

        user = cursor.fetchone()

    password_is_valid = (
        user is not None
        and bcrypt.checkpw(
            password.encode("utf-8"),
            user[4].encode("utf-8"),
        )
    )

    if not password_is_valid:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Invalid email or password.",
            },
            status_code=401,
        )

    request.session.clear()

    request.session["user"] = {
    "id": user[0],
    "full_name": user[1],
    "email": user[2],
    "university_id": user[3],
    "role": user[5],
}

    return RedirectResponse(
        url=dashboard_for_role(user[5]),
        status_code=303,
    )


@app.post("/logout", include_in_schema=False)
def logout(request: Request):
    request.session.clear()

    return RedirectResponse(
        url="/login",
        status_code=303,
    )
@app.get("/me")
def current_user(request: Request):
    user = require_session_user(request)

    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "university_id": user["university_id"],
        "role": user["role"],
    }
@app.get(
    "/admin-dashboard",
    include_in_schema=False,
)
def admin_dashboard_page(request: Request):
    user = require_session_user(
        request,
        allowed_roles=("admin",),
    )

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "user": user,
        },
    )
@app.get("/admin/overview")
def admin_overview(request: Request):
    require_session_user(
        request,
        allowed_roles=("admin",),
    )

    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'answered' THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END),
                COUNT(*)
            FROM questions
            """
        )

        question_counts = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) FROM answers")
        answer_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM categories")
        category_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM knowledge_entries"
        )
        knowledge_count = cursor.fetchone()[0]

    return {
        "users": user_count,
        "questions": {
            "open": question_counts[0] or 0,
            "assigned": question_counts[1] or 0,
            "answered": question_counts[2] or 0,
            "closed": question_counts[3] or 0,
            "total": question_counts[4] or 0,
        },
        "answers": answer_count,
        "categories": category_count,
        "knowledge_entries": knowledge_count,
    }
@app.get("/admin/users")
def admin_users(request: Request):
    require_session_user(
        request,
        allowed_roles=("admin",),
    )

    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                users.id,
                users.university_id,
                users.full_name,
                users.email,
                roles.name,
                users.is_active,
                users.created_at
            FROM users
            JOIN roles
                ON users.role_id = roles.id
            ORDER BY users.id
            """
        )

        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "university_id": row[1],
            "full_name": row[2],
            "email": row[3],
            "role": row[4],
            "is_active": bool(row[5]),
            "created_at": row[6],
        }
        for row in rows
    ]