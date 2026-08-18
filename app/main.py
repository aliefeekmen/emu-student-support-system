from pathlib import Path
from uuid import uuid4
import os
import bcrypt
import sqlite3
from dotenv import load_dotenv
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.ai_service import (
    AIConfigurationError,
    AIProviderError,
    build_prompt_context,
    find_similar_entries,
    generate_ai_answer,
)
from app.database import (
    close_question_assignment,
    connect_database,
    record_question_assignment,
    write_audit_log,
)


project_folder = Path(__file__).resolve().parent.parent
load_dotenv(project_folder / ".env")

session_secret = os.getenv("SESSION_SECRET")

if not session_secret:
    raise RuntimeError(
        "SESSION_SECRET environment variable is required."
    )
database_path = project_folder / "database" / "emu_chatbot.db"
uploads_path = project_folder / "uploads"
uploads_path.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="EMU Student Support API",
    description="Backend API for the EMU student support system.",
    version="1.1.0",
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
        "message": "EMU Student Support API is running."
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
            SELECT
                id,
                name_tr,
                name_en,
                description,
                responsible_unit,
                is_active
            FROM categories
            WHERE is_active = 1
            ORDER BY name_tr
            """
        )

        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "name_tr": row[1],
            "name_en": row[2],
            "description": row[3],
            "responsible_unit": row[4],
            "is_active": bool(row[5]),
        }
        for row in rows
    ]


@app.get("/subcategories")
def list_subcategories(
    request: Request,
    category_id: int | None = None,
):
    require_session_user(
        request,
        allowed_roles=("student", "staff", "admin"),
    )

    parameters: list[int] = []
    category_filter = ""

    if category_id is not None:
        category_filter = "AND category_id = ?"
        parameters.append(category_id)

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                id,
                category_id,
                name_tr,
                name_en,
                is_active
            FROM subcategories
            WHERE is_active = 1
            {category_filter}
            ORDER BY name_tr, id
            """,
            parameters,
        ).fetchall()

    return [
        {
            "id": row[0],
            "category_id": row[1],
            "name_tr": row[2],
            "name_en": row[3],
            "is_active": bool(row[4]),
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
    subcategory_id: int | None = Field(
        default=None,
        gt=0,
    )
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
    with connect_database(database_path) as connection:
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
              AND is_active = 1
            """,
            (question.category_id,),
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid category.",
            )

        if question.subcategory_id is not None:
            cursor.execute(
                """
                SELECT id
                FROM subcategories
                WHERE id = ?
                  AND category_id = ?
                  AND is_active = 1
                """,
                (
                    question.subcategory_id,
                    question.category_id,
                ),
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Invalid subcategory for the selected "
                        "category."
                    ),
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
                subcategory_id,
                language_id,
                subject,
                question_text
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                question.student_id,
                question.category_id,
                question.subcategory_id,
                language[0],
                question.subject.strip(),
                question.question_text.strip(),
            ),
        )

        question_id = cursor.lastrowid
        write_audit_log(
            connection,
            user_id=user["id"],
            action="question_created",
            entity_type="question",
            entity_id=question_id,
        )
        connection.commit()

    return {
        "id": question_id,
        "subcategory_id": question.subcategory_id,
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
                categories.id,
                categories.name_tr,
                categories.name_en,
                languages.code,
                staff.full_name,
                questions.created_at,
                subcategories.id,
                subcategories.name_tr,
                subcategories.name_en,
                questions.answered_at
            FROM questions
            JOIN users AS students
                ON questions.student_id = students.id
            JOIN categories
                ON questions.category_id = categories.id
            JOIN languages
                ON questions.language_id = languages.id
            LEFT JOIN users AS staff
                ON questions.assigned_staff_id = staff.id
            LEFT JOIN subcategories
                ON questions.subcategory_id = subcategories.id
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
            "category_id": row[5],
            "category": row[6],
            "category_en": row[7],
            "language": row[8],
            "assigned_staff": row[9],
            "created_at": row[10],
            "subcategory": (
                {
                    "id": row[11],
                    "name_tr": row[12],
                    "name_en": row[13],
                }
                if row[11] is not None
                else None
            ),
            "answered_at": row[14],
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
    with connect_database(database_path) as connection:
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

        record_question_assignment(
            connection,
            question_id=question_id,
            assigned_to_user_id=assignment.staff_id,
        )
        write_audit_log(
            connection,
            user_id=user["id"],
            action="question_assigned",
            entity_type="question",
            entity_id=question_id,
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
    ai_suggestion_id: int | None = Field(
        default=None,
        gt=0,
    )


@app.post(
    "/questions/{question_id}/ai-suggestion",
    status_code=201,
)
def create_ai_suggestion(
    request: Request,
    question_id: int,
):
    user = require_session_user(
        request,
        allowed_roles=("staff", "admin"),
    )

    with sqlite3.connect(database_path) as connection:
        question = connection.execute(
            """
            SELECT
                questions.subject,
                questions.question_text,
                languages.code,
                categories.id,
                categories.name_tr,
                categories.name_en
            FROM questions
            JOIN languages
                ON questions.language_id = languages.id
            JOIN categories
                ON questions.category_id = categories.id
            WHERE questions.id = ?
            """,
            (question_id,),
        ).fetchone()

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found.",
        )

    sources = find_similar_entries(
        database_path,
        subject=question[0],
        question_text=question[1],
        language=question[2],
        category_id=question[3],
        limit=3,
    )

    if not sources:
        raise HTTPException(
            status_code=404,
            detail="No institutional records were found.",
        )

    prompt_context = build_prompt_context(sources)
    category_name = (
        question[4] if question[2] == "tr" else question[5]
    )

    try:
        suggestion_text, model_name = generate_ai_answer(
            subject=question[0],
            question_text=question[1],
            language=question[2],
            category_name=category_name,
            prompt_context=prompt_context,
        )
    except AIConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error
    except AIProviderError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    with connect_database(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO ai_suggestions (
                question_id,
                provider,
                model_name,
                prompt_context,
                suggestion_text
            )
            VALUES (?, 'groq', ?, ?, ?)
            """,
            (
                question_id,
                model_name,
                prompt_context,
                suggestion_text,
            ),
        )
        suggestion_id = cursor.lastrowid
        write_audit_log(
            connection,
            user_id=user["id"],
            action="ai_suggestion_generated",
            entity_type="ai_suggestion",
            entity_id=suggestion_id,
        )
        connection.commit()

    return {
        "id": suggestion_id,
        "question_id": question_id,
        "provider": "groq",
        "model": model_name,
        "suggestion": suggestion_text,
        "sources": sources,
    }


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

    if answer.used_ai_suggestion and answer.ai_suggestion_id is None:
        raise HTTPException(
            status_code=400,
            detail="AI suggestion ID is required.",
        )

    if (
        not answer.used_ai_suggestion
        and answer.ai_suggestion_id is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="AI suggestion ID was provided but not used.",
        )

    with connect_database(database_path) as connection:
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

        if answer.ai_suggestion_id is not None:
            cursor.execute(
                """
                SELECT id
                FROM ai_suggestions
                WHERE id = ?
                  AND question_id = ?
                """,
                (
                    answer.ai_suggestion_id,
                    question_id,
                ),
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid AI suggestion for this question.",
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

        if answer.ai_suggestion_id is not None:
            cursor.execute(
                """
                UPDATE ai_suggestions
                SET
                    accepted = 1,
                    was_used = 1
                WHERE id = ?
                """,
                (answer.ai_suggestion_id,),
            )

        cursor.execute(
            """
            UPDATE questions
            SET
                status = 'answered',
                updated_at = CURRENT_TIMESTAMP,
                answered_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (question_id,),
        )

        close_question_assignment(
            connection,
            question_id=question_id,
        )
        write_audit_log(
            connection,
            user_id=user["id"],
            action="answer_created",
            entity_type="answer",
            entity_id=answer_id,
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
                categories.id,
                categories.name_tr,
                categories.name_en,
                languages.code,
                staff.full_name,
                questions.created_at,
                questions.updated_at,
                subcategories.id,
                subcategories.name_tr,
                subcategories.name_en,
                questions.answered_at
            FROM questions
            JOIN users AS students
                ON questions.student_id = students.id
            JOIN categories
                ON questions.category_id = categories.id
            JOIN languages
                ON questions.language_id = languages.id
            LEFT JOIN users AS staff
                ON questions.assigned_staff_id = staff.id
            LEFT JOIN subcategories
                ON questions.subcategory_id = subcategories.id
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

        cursor.execute(
            """
            SELECT
                question_assignments.id,
                users.id,
                users.full_name,
                question_assignments.assigned_at,
                question_assignments.is_active
            FROM question_assignments
            JOIN users
                ON question_assignments.assigned_to_user_id = users.id
            WHERE question_assignments.question_id = ?
            ORDER BY question_assignments.id
            """,
            (question_id,),
        )

        assignment_rows = cursor.fetchall()

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

    assignment_history = [
        {
            "id": row[0],
            "assigned_to_user_id": row[1],
            "assigned_to_name": row[2],
            "assigned_at": row[3],
            "is_active": bool(row[4]),
        }
        for row in assignment_rows
    ]

    return {
        "id": question[0],
        "subject": question[1],
        "question_text": question[2],
        "status": question[3],
        "student_name": question[4],
        "student_number": question[5],
                "category": {
            "id": question[6],
            "name_tr": question[7],
            "name_en": question[8],
        },
        "language": question[9],
        "assigned_staff": question[10],
        "created_at": question[11],
        "updated_at": question[12],
        "subcategory": (
            {
                "id": question[13],
                "name_tr": question[14],
                "name_en": question[15],
            }
            if question[13] is not None
            else None
        ),
        "answered_at": question[16],
        "assignment_history": assignment_history,
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

                ,subcategories.id
                ,subcategories.name_tr
                ,subcategories.name_en
                ,questions.answered_at

            FROM questions

            JOIN categories
                ON questions.category_id = categories.id

            JOIN languages
                ON questions.language_id = languages.id

            LEFT JOIN users AS staff
                ON questions.assigned_staff_id = staff.id

            LEFT JOIN subcategories
                ON questions.subcategory_id = subcategories.id

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
            "subcategory": (
                {
                    "id": row[13],
                    "name_tr": row[14],
                    "name_en": row[15],
                }
                if row[13] is not None
                else None
            ),
            "answered_at": row[16],
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
        with connect_database(database_path) as connection:
            write_audit_log(
                connection,
                user_id=(user[0] if user is not None else None),
                action="login_failed",
                entity_type="user",
                entity_id=(user[0] if user is not None else None),
            )
            connection.commit()

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Invalid email or password.",
            },
            status_code=401,
        )

    request.session.clear()

    with connect_database(database_path) as connection:
        write_audit_log(
            connection,
            user_id=user[0],
            action="login_succeeded",
            entity_type="user",
            entity_id=user[0],
        )
        connection.commit()

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
    user = request.session.get("user")

    if user:
        with connect_database(database_path) as connection:
            write_audit_log(
                connection,
                user_id=user["id"],
                action="logout",
                entity_type="user",
                entity_id=user["id"],
            )
            connection.commit()

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
            "SELECT COUNT(*) FROM subcategories"
        )
        subcategory_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM audit_logs")
        audit_log_count = cursor.fetchone()[0]

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
        "subcategories": subcategory_count,
        "audit_logs": audit_log_count,
        "knowledge_entries": knowledge_count,
    }
class AdminUserCreate(BaseModel):
    university_id: str | None = Field(
        default=None,
        max_length=50,
    )
    full_name: str = Field(
        min_length=2,
        max_length=100,
    )
    email: str = Field(
        min_length=5,
        max_length=150,
    )
    password: str = Field(
        min_length=8,
        max_length=128,
    )
    role: str = Field(
        min_length=3,
        max_length=20,
    )


class AdminUserRoleUpdate(BaseModel):
    role: str = Field(
        min_length=3,
        max_length=20,
    )


@app.post("/admin/users", status_code=201)
def create_admin_user(
    request: Request,
    new_user: AdminUserCreate,
):
    current_user = require_session_user(
        request,
        allowed_roles=("admin",),
    )

    full_name = new_user.full_name.strip()
    email = new_user.email.strip().lower()
    role_name = new_user.role.strip().lower()

    university_id = (
        new_user.university_id.strip()
        if new_user.university_id
        else None
    )

    if not full_name:
        raise HTTPException(
            status_code=400,
            detail="Full name is required.",
        )

    if "@" not in email:
        raise HTTPException(
            status_code=400,
            detail="A valid email address is required.",
        )

    if role_name not in (
        "student",
        "staff",
        "admin",
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid user role.",
        )

    password_hash = bcrypt.hashpw(
        new_user.password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    with connect_database(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM roles
            WHERE name = ?
            """,
            (role_name,),
        )

        role_record = cursor.fetchone()

        if role_record is None:
            raise HTTPException(
                status_code=400,
                detail="User role was not found.",
            )

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE lower(email) = lower(?)
            """,
            (email,),
        )

        if cursor.fetchone() is not None:
            raise HTTPException(
                status_code=409,
                detail="Email address is already in use.",
            )

        if university_id:
            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE university_id = ?
                """,
                (university_id,),
            )

            if cursor.fetchone() is not None:
                raise HTTPException(
                    status_code=409,
                    detail="University ID is already in use.",
                )

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
            """,
            (
                university_id,
                full_name,
                email,
                password_hash,
                role_record[0],
            ),
        )

        user_id = cursor.lastrowid
        write_audit_log(
            connection,
            user_id=current_user["id"],
            action="user_created",
            entity_type="user",
            entity_id=user_id,
        )
        connection.commit()

    return {
        "id": user_id,
        "university_id": university_id,
        "full_name": full_name,
        "email": email,
        "role": role_name,
        "is_active": True,
        "message": "User created successfully.",
    }


@app.patch("/admin/users/{user_id}/role")
def update_admin_user_role(
    request: Request,
    user_id: int,
    role_update: AdminUserRoleUpdate,
):
    current_user = require_session_user(
        request,
        allowed_roles=("admin",),
    )

    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own role.",
        )

    role_name = role_update.role.strip().lower()

    if role_name not in (
        "student",
        "staff",
        "admin",
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid user role.",
        )

    with connect_database(database_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="User not found.",
            )

        cursor.execute(
            """
            SELECT id
            FROM roles
            WHERE name = ?
            """,
            (role_name,),
        )

        role_record = cursor.fetchone()

        if role_record is None:
            raise HTTPException(
                status_code=400,
                detail="User role was not found.",
            )

        cursor.execute(
            """
            UPDATE users
            SET role_id = ?
            WHERE id = ?
            """,
            (
                role_record[0],
                user_id,
            ),
        )

        write_audit_log(
            connection,
            user_id=current_user["id"],
            action="user_role_updated",
            entity_type="user",
            entity_id=user_id,
        )

        connection.commit()

    return {
        "id": user_id,
        "role": role_name,
        "message": "User role updated successfully.",
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


@app.get("/admin/audit-logs")
def admin_audit_logs(
    request: Request,
    limit: int = 100,
    offset: int = 0,
):
    require_session_user(
        request,
        allowed_roles=("admin",),
    )

    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                audit_logs.id,
                audit_logs.user_id,
                users.full_name,
                audit_logs.action,
                audit_logs.entity_type,
                audit_logs.entity_id,
                audit_logs.timestamp
            FROM audit_logs
            LEFT JOIN users
                ON audit_logs.user_id = users.id
            ORDER BY audit_logs.id DESC
            LIMIT ? OFFSET ?
            """,
            (
                limit,
                offset,
            ),
        ).fetchall()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "user_name": row[2],
            "action": row[3],
            "entity_type": row[4],
            "entity_id": row[5],
            "timestamp": row[6],
        }
        for row in rows
    ]
@app.post(
    "/questions/{question_id}/attachments",
    status_code=201,
)
async def upload_question_attachment(
    question_id: int,
    request: Request,
    file: UploadFile = File(...),
):
    user = require_session_user(
        request,
        allowed_roles=("student",),
    )

    with sqlite3.connect(database_path) as connection:
        question_record = connection.execute(
            """
            SELECT id, student_id
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        ).fetchone()

    if question_record is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found.",
        )

    if question_record[1] != user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You can only add attachments to your own questions.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A file name is required.",
        )

    original_name = Path(file.filename).name
    file_extension = Path(original_name).suffix.lower()

    allowed_extensions = {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".doc",
        ".docx",
    }

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type.",
        )

    maximum_file_size = 5 * 1024 * 1024
    file_content = await file.read(
        maximum_file_size + 1
    )
    await file.close()

    if len(file_content) > maximum_file_size:
        raise HTTPException(
            status_code=400,
            detail="File size cannot exceed 5 MB.",
        )

    stored_name = f"{uuid4().hex}{file_extension}"
    stored_path = uploads_path / stored_name
    relative_path = f"uploads/{stored_name}"

    stored_path.write_bytes(file_content)

    try:
        with connect_database(database_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO attachments (
                    question_id,
                    file_name,
                    file_path,
                    mime_type,
                    file_size
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    original_name,
                    relative_path,
                    file.content_type,
                    len(file_content),
                ),
            )
            attachment_id = cursor.lastrowid
            write_audit_log(
                connection,
                user_id=user["id"],
                action="attachment_uploaded",
                entity_type="attachment",
                entity_id=attachment_id,
            )
            connection.commit()
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise

    return {
        "id": attachment_id,
        "question_id": question_id,
        "file_name": original_name,
        "mime_type": file.content_type,
        "size": len(file_content),
        "message": "Attachment uploaded successfully.",
    }
@app.get("/questions/{question_id}/attachments")
def list_question_attachments(
    question_id: int,
    request: Request,
):
    user = require_session_user(
        request,
        allowed_roles=("student", "staff", "admin"),
    )

    with sqlite3.connect(database_path) as connection:
        question_record = connection.execute(
            """
            SELECT id, student_id
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        ).fetchone()

        if question_record is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found.",
            )

        if (
            user["role"] == "student"
            and question_record[1] != user["id"]
        ):
            raise HTTPException(
                status_code=403,
                detail="You can only view attachments for your own questions.",
            )

        attachment_rows = connection.execute(
            """
            SELECT
                id,
                file_name,
                mime_type,
                file_size,
                uploaded_at
            FROM attachments
            WHERE question_id = ?
            ORDER BY uploaded_at DESC, id DESC
            """,
            (question_id,),
        ).fetchall()

    return [
        {
            "id": row[0],
            "question_id": question_id,
            "file_name": row[1],
            "mime_type": row[2],
            "size": row[3],
            "uploaded_at": row[4],
            "download_url": (
                f"/attachments/{row[0]}/download"
            ),
        }
        for row in attachment_rows
    ]


@app.get("/attachments/{attachment_id}/download")
def download_question_attachment(
    attachment_id: int,
    request: Request,
):
    user = require_session_user(
        request,
        allowed_roles=("student", "staff", "admin"),
    )

    with sqlite3.connect(database_path) as connection:
        attachment_record = connection.execute(
            """
            SELECT
                attachments.file_name,
                attachments.file_path,
                attachments.mime_type,
                questions.student_id
            FROM attachments
            JOIN questions
                ON questions.id = attachments.question_id
            WHERE attachments.id = ?
            """,
            (attachment_id,),
        ).fetchone()

    if attachment_record is None:
        raise HTTPException(
            status_code=404,
            detail="Attachment not found.",
        )

    if (
        user["role"] == "student"
        and attachment_record[3] != user["id"]
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only download attachments from your own questions.",
        )

    stored_path = (
        project_folder / attachment_record[1]
    ).resolve()
    resolved_uploads_path = uploads_path.resolve()

    if not stored_path.is_relative_to(
        resolved_uploads_path
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid attachment path.",
        )

    if not stored_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Attachment file not found.",
        )

    return FileResponse(
        path=stored_path,
        media_type=(
            attachment_record[2]
            or "application/octet-stream"
        ),
        filename=attachment_record[0],
    )
class CategoryCreate(BaseModel):
    name_tr: str = Field(
        min_length=2,
        max_length=150,
    )
    name_en: str = Field(
        min_length=2,
        max_length=150,
    )
    description: str | None = Field(
        default=None,
        max_length=500,
    )
    responsible_unit: str | None = Field(
        default=None,
        max_length=200,
    )


class SubcategoryCreate(BaseModel):
    category_id: int = Field(gt=0)
    name_tr: str = Field(
        min_length=2,
        max_length=150,
    )
    name_en: str = Field(
        min_length=2,
        max_length=150,
    )


class QuestionCategoryUpdate(BaseModel):
    category_id: int = Field(gt=0)


@app.post("/categories", status_code=201)
def create_category(
    request: Request,
    category: CategoryCreate,
):
    current_user = require_session_user(
        request,
        allowed_roles=("admin",),
    )

    name_tr = " ".join(
        category.name_tr.split()
    )
    name_en = " ".join(
        category.name_en.split()
    )
    description = (
        " ".join(category.description.split())
        if category.description
        else None
    )
    responsible_unit = (
        " ".join(category.responsible_unit.split())
        if category.responsible_unit
        else None
    )

    with connect_database(database_path) as connection:
        cursor = connection.cursor()

        existing_categories = cursor.execute(
            """
            SELECT id, name_tr, name_en
            FROM categories
            """
        ).fetchall()

        duplicate_exists = any(
            row[1].casefold() == name_tr.casefold()
            or row[2].casefold() == name_en.casefold()
            for row in existing_categories
        )

        if duplicate_exists:
            raise HTTPException(
                status_code=409,
                detail="A category with this name already exists.",
            )

        try:
            cursor.execute(
                """
                INSERT INTO categories (
                    name_tr,
                    name_en,
                    description,
                    responsible_unit
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    name_tr,
                    name_en,
                    description,
                    responsible_unit,
                ),
            )
            category_id = cursor.lastrowid
            write_audit_log(
                connection,
                user_id=current_user["id"],
                action="category_created",
                entity_type="category",
                entity_id=category_id,
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                status_code=409,
                detail="A category with this name already exists.",
            ) from error

    return {
        "id": category_id,
        "name_tr": name_tr,
        "name_en": name_en,
        "description": description,
        "responsible_unit": responsible_unit,
        "is_active": True,
        "message": "Category created successfully.",
    }


@app.post("/subcategories", status_code=201)
def create_subcategory(
    request: Request,
    subcategory: SubcategoryCreate,
):
    current_user = require_session_user(
        request,
        allowed_roles=("admin",),
    )

    name_tr = " ".join(subcategory.name_tr.split())
    name_en = " ".join(subcategory.name_en.split())

    with connect_database(database_path) as connection:
        category_record = connection.execute(
            """
            SELECT id
            FROM categories
            WHERE id = ?
              AND is_active = 1
            """,
            (subcategory.category_id,),
        ).fetchone()

        if category_record is None:
            raise HTTPException(
                status_code=400,
                detail="Active category required.",
            )

        duplicate = connection.execute(
            """
            SELECT id
            FROM subcategories
            WHERE category_id = ?
              AND (
                  lower(name_tr) = lower(?)
                  OR lower(name_en) = lower(?)
              )
            """,
            (
                subcategory.category_id,
                name_tr,
                name_en,
            ),
        ).fetchone()

        if duplicate is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "A subcategory with this name already exists "
                    "for the category."
                ),
            )

        try:
            cursor = connection.execute(
                """
                INSERT INTO subcategories (
                    category_id,
                    name_tr,
                    name_en
                )
                VALUES (?, ?, ?)
                """,
                (
                    subcategory.category_id,
                    name_tr,
                    name_en,
                ),
            )
            subcategory_id = cursor.lastrowid
            write_audit_log(
                connection,
                user_id=current_user["id"],
                action="subcategory_created",
                entity_type="subcategory",
                entity_id=subcategory_id,
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                status_code=409,
                detail=(
                    "A subcategory with this name already exists "
                    "for the category."
                ),
            ) from error

    return {
        "id": subcategory_id,
        "category_id": subcategory.category_id,
        "name_tr": name_tr,
        "name_en": name_en,
        "is_active": True,
        "message": "Subcategory created successfully.",
    }


@app.patch(
    "/questions/{question_id}/category"
)
def update_question_category(
    question_id: int,
    request: Request,
    category: QuestionCategoryUpdate,
):
    current_user = require_session_user(
        request,
        allowed_roles=("staff", "admin"),
    )

    with connect_database(database_path) as connection:
        cursor = connection.cursor()

        question_record = cursor.execute(
            """
            SELECT id
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        ).fetchone()

        if question_record is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found.",
            )

        category_record = cursor.execute(
            """
            SELECT id, name_tr, name_en
            FROM categories
            WHERE id = ?
              AND is_active = 1
            """,
            (category.category_id,),
        ).fetchone()

        if category_record is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid category.",
            )

        cursor.execute(
            """
            UPDATE questions
            SET
                category_id = ?,
                subcategory_id = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                category.category_id,
                question_id,
            ),
        )
        write_audit_log(
            connection,
            user_id=current_user["id"],
            action="question_category_updated",
            entity_type="question",
            entity_id=question_id,
        )
        connection.commit()

    return {
        "question_id": question_id,
        "category": {
            "id": category_record[0],
            "name_tr": category_record[1],
            "name_en": category_record[2],
        },
        "message": "Question category updated successfully.",
    }
