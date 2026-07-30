import os
import sqlite3

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
            "password": "Staff123!",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303


def login_as_student():
    response = client.post(
        "/login",
        data={
            "email": "student@demo.local",
            "password": "Student123!",
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
    assert data["knowledge_entries"] == 769
    assert data["categories"] == 31
    assert data["languages"] == 2


def test_categories_endpoint():
    login_as_student()

    response = client.get("/categories")
    categories = response.json()

    assert response.status_code == 200
    assert len(categories) == 31


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

    response = client.get("/knowledge/7136")
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == 7136
    assert data["language"] == "tr"


def test_get_missing_knowledge_entry():
    login_as_staff()

    response = client.get("/knowledge/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Knowledge entry not found."
    }


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
            "password": "Admin123!",
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
    assert data["users"] == 3
    assert data["categories"] == 31
    assert data["knowledge_entries"] == 769


def test_staff_cannot_access_admin_endpoint():
    client.post("/logout")

    client.post(
        "/login",
        data={
            "email": "staff@demo.local",
            "password": "Staff123!",
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
            "password": "Student123!",
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