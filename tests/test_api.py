import os
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


os.environ.setdefault(
    "SESSION_SECRET",
    "test-only-session-secret",
)

from app.main import app, database_path


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_session_cookies():
    client.cookies.clear()
    yield
    client.cookies.clear()


def login_as_staff():
    response = client.post(
        "/login",
        data={
            "email": "staff@demo.local",
            "password": "123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303


def login_as_student():
    response = client.post(
        "/login",
        data={
            "email": "student@demo.local",
            "password": "123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }


def test_schema_v2_is_installed():
    with sqlite3.connect(database_path) as connection:
        schema_version = connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }
        question_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(questions)"
            )
        }

    assert schema_version == 2
    assert {
        "subcategories",
        "question_assignments",
        "audit_logs",
    }.issubset(tables)
    assert {
        "subcategory_id",
        "answered_at",
    }.issubset(question_columns)


def test_login_page():
    response = client.get("/login")

    assert response.status_code == 200
    assert "Sign in to your account" in response.text


def test_protected_endpoint_requires_login():
    response = client.get("/categories")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required."
    }


def test_statistics_endpoint():
    login_as_staff()

    response = client.get("/stats")
    data = response.json()

    assert response.status_code == 200
    assert data["knowledge_entries"] == 744
    assert data["categories"] >= 31
    assert data["languages"] == 2


def test_categories_endpoint():
    login_as_student()

    response = client.get("/categories")
    categories = response.json()

    assert response.status_code == 200
    assert len(categories) >= 31


def test_knowledge_search():
    login_as_staff()

    response = client.get(
        "/knowledge",
        params={
            "language": "tr",
            "search": "portal",
            "limit": 5,
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["total"] > 0
    assert data["limit"] == 5
    assert len(data["items"]) <= 5

    for item in data["items"]:
        assert item["language"] == "tr"


def test_get_existing_knowledge_entry():
    login_as_staff()

    response = client.get("/knowledge/1")
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == 1
    assert data["language"] == "tr"


def test_get_missing_knowledge_entry():
    login_as_staff()

    response = client.get("/knowledge/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Knowledge entry not found."
    }


def test_staff_can_generate_ai_suggestion(monkeypatch):
    question_id = None

    def fake_generate_ai_answer(**kwargs):
        assert "Approved answer:" in kwargs["prompt_context"]
        return (
            "This is a reviewed AI answer suggestion.",
            "openai/gpt-oss-20b",
        )

    monkeypatch.setattr(
        "app.main.generate_ai_answer",
        fake_generate_ai_answer,
    )

    try:
        login_as_student()
        question_response = client.post(
            "/questions",
            json={
                "student_id": 1,
                "category_id": 15,
                "language": "tr",
                "subject": "Yatay geçiş bursu",
                "question_text": (
                    "Yatay geçiş yaparsam burs durumum ne olur?"
                ),
            },
        )
        assert question_response.status_code == 201
        question_id = question_response.json()["id"]

        client.post("/logout")
        login_as_staff()

        response = client.post(
            f"/questions/{question_id}/ai-suggestion"
        )
        data = response.json()

        assert response.status_code == 201
        assert data["provider"] == "groq"
        assert data["model"] == "openai/gpt-oss-20b"
        assert data["suggestion"] == (
            "This is a reviewed AI answer suggestion."
        )
        assert len(data["sources"]) == 3

        with sqlite3.connect(database_path) as connection:
            saved_suggestion = connection.execute(
                """
                SELECT suggestion_text
                FROM ai_suggestions
                WHERE id = ?
                """,
                (data["id"],),
            ).fetchone()

        assert saved_suggestion[0] == data["suggestion"]
    finally:
        cleanup_category_test(question_id=question_id)


def test_expert_dashboard_page():
    login_as_staff()

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Student Q&A Center" in response.text
    assert "Expert Panel" in response.text
    assert "Demo Staff" in response.text


def test_student_dashboard_page():
    login_as_student()

    response = client.get("/student-dashboard")

    assert response.status_code == 200
    assert "Student Q&A Center" in response.text
    assert "Ask New Question" in response.text
    assert "Demo Student" in response.text


def test_current_user_endpoint():
    login_as_staff()

    response = client.get("/me")
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == 2
    assert data["role"] == "staff"


def test_dashboard_stylesheet():
    response = client.get(
        "/static/css/dashboard.css"
    )

    assert response.status_code == 200
    assert ".app-shell" in response.text
    assert ".login-layout" in response.text

def login_as_admin():
    return client.post(
        "/login",
        data={
            "email": "admin@demo.local",
            "password": "123",
        },
        follow_redirects=False,
    )


def test_admin_dashboard_page():
    login_as_admin()

    response = client.get("/admin-dashboard")

    assert response.status_code == 200


def test_admin_overview_endpoint():
    login_as_admin()

    response = client.get("/admin/overview")
    data = response.json()

    assert response.status_code == 200
    assert data["users"] >= 3
    assert data["categories"] >= 31
    assert data["knowledge_entries"] == 744


def test_staff_cannot_access_admin_endpoint():
    client.post("/logout")

    client.post(
        "/login",
        data={
            "email": "staff@demo.local",
            "password": "123",
        },
    )

    response = client.get("/admin/overview")

    assert response.status_code == 403


def test_student_redirected_from_expert_dashboard():
    client.post("/logout")

    client.post(
        "/login",
        data={
            "email": "student@demo.local",
            "password": "123",
        },
    )

    response = client.get(
        "/dashboard",
        follow_redirects=False,
    )

    assert response.status_code in (302, 303, 307)
    assert response.headers["location"] == "/student-dashboard"
def test_student_can_upload_question_attachment():
    login_as_student()

    question_response = client.post(
        "/questions",
        json={
            "student_id": 1,
            "category_id": 15,
            "language": "tr",
            "subject": "Attachment test question",
            "question_text": (
                "This question is created for the attachment test."
            ),
        },
    )

    assert question_response.status_code == 201

    question_id = question_response.json()["id"]
    attachment_id = None

    try:
        response = client.post(
            f"/questions/{question_id}/attachments",
            files={
                "file": (
                    "test_document.pdf",
                    b"%PDF-1.4 test document",
                    "application/pdf",
                )
            },
        )
        data = response.json()

        assert response.status_code == 201
        assert data["question_id"] == question_id
        assert data["file_name"] == "test_document.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["size"] > 0

        attachment_id = data["id"]

        list_response = client.get(
            f"/questions/{question_id}/attachments"
        )
        attachment_list = list_response.json()

        assert list_response.status_code == 200
        assert len(attachment_list) == 1
        assert attachment_list[0]["id"] == attachment_id
        assert (
            attachment_list[0]["file_name"]
            == "test_document.pdf"
        )
        assert attachment_list[0]["size"] > 0

        download_response = client.get(
            f"/attachments/{attachment_id}/download"
        )

        assert download_response.status_code == 200
        assert (
            download_response.content
            == b"%PDF-1.4 test document"
        )
        assert (
            "test_document.pdf"
            in download_response.headers[
                "content-disposition"
            ]
        )
    finally:
        with sqlite3.connect(database_path) as connection:
            if attachment_id is not None:
                attachment_record = connection.execute(
                    """
                    SELECT file_path
                    FROM attachments
                    WHERE id = ?
                    """,
                    (attachment_id,),
                ).fetchone()

                if attachment_record is not None:
                    stored_path = (
                        database_path.parent.parent
                        / attachment_record[0]
                    )
                    stored_path.unlink(missing_ok=True)

                connection.execute(
                    """
                    DELETE FROM attachments
                    WHERE id = ?
                    """,
                    (attachment_id,),
                )

            connection.execute(
                """
                DELETE FROM questions
                WHERE id = ?
                """,
                (question_id,),
            )
            connection.commit()


def test_staff_cannot_upload_question_attachment():
    login_as_staff()

    response = client.post(
        "/questions/1/attachments",
        files={
            "file": (
                "test_document.pdf",
                b"%PDF-1.4 test document",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 403
def cleanup_category_test(
    question_id=None,
    subcategory_id=None,
    category_id=None,
):
    with sqlite3.connect(database_path) as connection:
        if question_id is not None:
            connection.execute(
                """
                DELETE FROM ai_suggestions
                WHERE question_id = ?
                """,
                (question_id,),
            )
            connection.execute(
                """
                DELETE FROM question_assignments
                WHERE question_id = ?
                """,
                (question_id,),
            )
            connection.execute(
                """
                DELETE FROM answers
                WHERE question_id = ?
                """,
                (question_id,),
            )
            connection.execute(
                """
                DELETE FROM attachments
                WHERE question_id = ?
                """,
                (question_id,),
            )
            connection.execute(
                """
                DELETE FROM questions
                WHERE id = ?
                """,
                (question_id,),
            )

        if subcategory_id is not None:
            connection.execute(
                """
                DELETE FROM subcategories
                WHERE id = ?
                """,
                (subcategory_id,),
            )

        if category_id is not None:
            connection.execute(
                """
                DELETE FROM categories
                WHERE id = ?
                """,
                (category_id,),
            )

        connection.commit()


def test_staff_can_assign_admin_created_category():
    unique_value = uuid4().hex[:8]
    question_id = None
    category_id = None

    try:
        login_as_student()

        question_response = client.post(
            "/questions",
            json={
                "student_id": 1,
                "category_id": 15,
                "language": "en",
                "subject": "Category assignment test",
                "question_text": (
                    "This question is created to test "
                    "category assignment."
                ),
            },
        )

        assert question_response.status_code == 201
        question_id = question_response.json()["id"]

        client.post("/logout")
        login_as_admin()

        category_data = {
            "name_tr": (
                f"Test Kategorisi {unique_value}"
            ),
            "name_en": (
                f"Test Category {unique_value}"
            ),
        }

        category_response = client.post(
            "/categories",
            json=category_data,
        )

        assert category_response.status_code == 201

        category_id = category_response.json()["id"]

        duplicate_response = client.post(
            "/categories",
            json=category_data,
        )

        assert duplicate_response.status_code == 409

        client.post("/logout")
        login_as_staff()

        update_response = client.patch(
            f"/questions/{question_id}/category",
            json={
                "category_id": category_id,
            },
        )
        update_data = update_response.json()

        assert update_response.status_code == 200
        assert update_data["question_id"] == question_id
        assert (
            update_data["category"]["id"]
            == category_id
        )

        detail_response = client.get(
            f"/questions/{question_id}"
        )

        assert detail_response.status_code == 200
        assert (
            detail_response.json()["category"]["id"]
            == category_id
        )
    finally:
        cleanup_category_test(
            question_id=question_id,
            category_id=category_id,
        )


def test_staff_cannot_create_category():
    login_as_staff()

    response = client.post(
        "/categories",
        json={
            "name_tr": "Yetkisiz Personel Kategorisi",
            "name_en": "Unauthorized Staff Category",
        },
    )

    assert response.status_code == 403


def test_admin_can_create_category():
    unique_value = uuid4().hex[:8]
    category_id = None

    try:
        login_as_admin()

        response = client.post(
            "/categories",
            json={
                "name_tr": (
                    f"Admin Test Kategorisi {unique_value}"
                ),
                "name_en": (
                    f"Admin Test Category {unique_value}"
                ),
                "description": "Schema v2 category test",
                "responsible_unit": "IT Directorate",
            },
        )

        assert response.status_code == 201

        response_data = response.json()
        category_id = response_data["id"]
        assert response_data["description"] == (
            "Schema v2 category test"
        )
        assert response_data["responsible_unit"] == (
            "IT Directorate"
        )
    finally:
        cleanup_category_test(
            category_id=category_id,
        )


def test_admin_can_create_subcategory_and_student_can_use_it():
    unique_value = uuid4().hex[:8]
    category_id = None
    subcategory_id = None
    question_id = None

    try:
        login_as_admin()

        category_response = client.post(
            "/categories",
            json={
                "name_tr": f"Alt Kategori Testi {unique_value}",
                "name_en": f"Subcategory Test {unique_value}",
            },
        )
        assert category_response.status_code == 201
        category_id = category_response.json()["id"]

        subcategory_response = client.post(
            "/subcategories",
            json={
                "category_id": category_id,
                "name_tr": f"Alt Başlık {unique_value}",
                "name_en": f"Subtopic {unique_value}",
            },
        )
        assert subcategory_response.status_code == 201
        subcategory_id = subcategory_response.json()["id"]

        client.post("/logout")
        login_as_student()

        list_response = client.get(
            "/subcategories",
            params={"category_id": category_id},
        )
        assert list_response.status_code == 200
        assert any(
            item["id"] == subcategory_id
            for item in list_response.json()
        )

        question_response = client.post(
            "/questions",
            json={
                "student_id": 1,
                "category_id": category_id,
                "subcategory_id": subcategory_id,
                "language": "en",
                "subject": "Subcategory workflow test",
                "question_text": (
                    "This question verifies the subcategory workflow."
                ),
            },
        )
        assert question_response.status_code == 201
        question_id = question_response.json()["id"]

        detail_response = client.get(
            f"/questions/{question_id}"
        )
        assert detail_response.status_code == 200
        assert (
            detail_response.json()["subcategory"]["id"]
            == subcategory_id
        )
    finally:
        cleanup_category_test(
            question_id=question_id,
            subcategory_id=subcategory_id,
            category_id=category_id,
        )


def test_assignment_history_and_answered_timestamp():
    question_id = None

    try:
        login_as_student()
        question_response = client.post(
            "/questions",
            json={
                "student_id": 1,
                "category_id": 15,
                "language": "en",
                "subject": "Assignment history test",
                "question_text": (
                    "This question verifies assignment history."
                ),
            },
        )
        assert question_response.status_code == 201
        question_id = question_response.json()["id"]

        client.post("/logout")
        login_as_staff()

        assign_response = client.patch(
            f"/questions/{question_id}/assign",
            json={"staff_id": 2},
        )
        assert assign_response.status_code == 200

        answer_response = client.post(
            f"/questions/{question_id}/answers",
            json={
                "staff_id": 2,
                "answer_text": "Assignment history verified.",
                "used_ai_suggestion": False,
            },
        )
        assert answer_response.status_code == 201

        detail_response = client.get(
            f"/questions/{question_id}"
        )
        detail = detail_response.json()

        assert detail_response.status_code == 200
        assert detail["status"] == "answered"
        assert detail["answered_at"] is not None
        assert len(detail["assignment_history"]) == 1
        assert detail["assignment_history"][0][
            "assigned_to_user_id"
        ] == 2
        assert detail["assignment_history"][0][
            "is_active"
        ] is False
    finally:
        cleanup_category_test(question_id=question_id)


def test_admin_can_view_audit_logs():
    login_as_admin()

    response = client.get("/admin/audit-logs")

    assert response.status_code == 200
    assert len(response.json()) > 0
    assert {
        "action",
        "entity_type",
        "timestamp",
    }.issubset(response.json()[0])


def test_staff_cannot_view_audit_logs():
    login_as_staff()

    response = client.get("/admin/audit-logs")

    assert response.status_code == 403


def test_student_cannot_create_category():
    login_as_student()

    response = client.post(
        "/categories",
        json={
            "name_tr": "Yetkisiz Test Kategorisi",
            "name_en": "Unauthorized Test Category",
        },
    )

    assert response.status_code == 403



def test_admin_can_create_user_and_update_role():
    unique_value = uuid4().hex[:8]
    user_id = None

    try:
        login_as_admin()

        create_response = client.post(
            "/admin/users",
            json={
                "university_id": (
                    f"TEST-{unique_value}"
                ),
                "full_name": "Test User",
                "email": (
                    f"test-{unique_value}@demo.local"
                ),
                "password": "TestPassword123!",
                "role": "student",
            },
        )

        create_data = create_response.json()

        assert create_response.status_code == 201
        assert create_data["full_name"] == "Test User"
        assert create_data["role"] == "student"

        user_id = create_data["id"]

        role_response = client.patch(
            f"/admin/users/{user_id}/role",
            json={
                "role": "staff",
            },
        )

        assert role_response.status_code == 200
        assert role_response.json()["role"] == "staff"

        users_response = client.get("/admin/users")
        users = users_response.json()

        created_user = next(
            user
            for user in users
            if user["id"] == user_id
        )

        assert created_user["role"] == "staff"
    finally:
        if user_id is not None:
            with sqlite3.connect(
                database_path
            ) as connection:
                connection.execute(
                    """
                    DELETE FROM users
                    WHERE id = ?
                    """,
                    (user_id,),
                )
                connection.commit()


def test_staff_cannot_create_user():
    login_as_staff()

    response = client.post(
        "/admin/users",
        json={
            "university_id": "UNAUTHORIZED-TEST",
            "full_name": "Unauthorized User",
            "email": "unauthorized@demo.local",
            "password": "TestPassword123!",
            "role": "student",
        },
    )

    assert response.status_code == 403


def test_admin_cannot_change_own_role():
    login_as_admin()

    response = client.patch(
        "/admin/users/3/role",
        json={
            "role": "staff",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "You cannot change your own role.",
    }
